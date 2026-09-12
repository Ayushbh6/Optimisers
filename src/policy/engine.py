"""Inventory policy calculation engine for (s, S) reorder rules.

Computes reorder points (s), order-up-to levels (S), safety stock, and EOQ lot sizes
from demand forecasts and explicit economic assumptions.
"""

import logging
from typing import Dict
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.policy.config import PolicyConfig, DEFAULT_POLICY_CONFIG

logger = logging.getLogger(__name__)


def compute_policy_vectors(
    mu_arr: np.ndarray,
    std_arr: np.ndarray,
    unit_costs: np.ndarray,
    lead_time_days: float,
    target_service_level: float,
    holding_cost_rate: float,
    k_line: float,
    moq: float,
    stocking_threshold: float,
) -> Dict[str, np.ndarray]:
    """Compute the core (s, S) policy vectors shared by the policy engine and the simulation.

    This is the single source of truth for the reorder-point / order-up-to maths,
    so the Phase 4 policy artifact and the Phase 5 walk-forward simulation can never
    drift apart on formula details (MOQ, safety stock, stocking threshold).

    Formulas:
      - z = Phi^{-1}(target_service_level)
      - Lead-time demand: mu_L = mu * L
      - Lead-time uncertainty: sigma_L = (std / sqrt(7)) * sqrt(L)
      - Safety stock: SS = max(z * sigma_L, 0.5)
      - Reorder point: s = ceil(mu_L + SS)
      - EOQ: ceil(sqrt(2 * D_annual * k_line / (holding_rate * unit_cost)))
      - Order quantity: Q = max(EOQ, MOQ)
      - Order-up-to: S = s + Q
      - Target stock: SS + Q / 2

    Args:
        mu_arr: Daily expected demand per pair.
        std_arr: Weekly demand standard deviation per pair.
        unit_costs: Wholesale unit cost per pair.
        lead_time_days: Supplier lead time in days.
        target_service_level: Cycle service level target.
        holding_cost_rate: Annual holding cost rate.
        k_line: Marginal ordering cost per SKU line item (used for EOQ lot sizing).
        moq: Minimum order quantity.
        stocking_threshold: Minimum daily demand velocity to stock a shelf.

    Returns:
        Dict of aligned numpy arrays with keys:
        'is_stocked', 'safety_stock', 'reorder_point_s', 'order_qty_q',
        'order_up_to_S', 'target_stock'.
    """
    L = float(lead_time_days)
    z = float(norm.ppf(target_service_level))
    r = float(holding_cost_rate)

    mu_L = mu_arr * L
    sigma_L = (std_arr / np.sqrt(7.0)) * np.sqrt(L)
    raw_safety_stock = np.maximum(z * sigma_L, 0.5)

    # A valid dated cost is any positive finite value.  Older code replaced
    # cheap items with EUR1, which changed the policy for real low-cost items.
    # Callers that have no usable cost must mark the policy unavailable; this
    # shared calculation therefore preserves the supplied value exactly.
    unit_cost = np.asarray(unit_costs, dtype=float)
    holding_per_unit = r * unit_cost
    annual_demand = mu_arr * 365.0
    with np.errstate(divide="ignore", invalid="ignore"):
        eoq = np.ceil(np.sqrt((2.0 * annual_demand * k_line) / holding_per_unit))
    order_qty = np.maximum(eoq, moq)

    is_stocked = (mu_arr >= stocking_threshold)
    safety_stock = np.where(is_stocked, raw_safety_stock, 0.0)
    reorder_point_s = np.where(is_stocked, np.ceil(mu_L + safety_stock), 0.0)
    order_qty_q = np.where(is_stocked, order_qty, 0.0)
    order_up_to_S = np.where(is_stocked, reorder_point_s + order_qty_q, 0.0)
    target_stock = np.where(is_stocked, safety_stock + order_qty_q / 2.0, 0.0)

    return {
        "is_stocked": is_stocked,
        "safety_stock": safety_stock,
        "reorder_point_s": reorder_point_s,
        "order_qty_q": order_qty_q,
        "order_up_to_S": order_up_to_S,
        "target_stock": target_stock,
    }


def compute_inventory_policy(
    forecast_df: pd.DataFrame,
    onhand_df: pd.DataFrame,
    config: PolicyConfig = DEFAULT_POLICY_CONFIG,
) -> pd.DataFrame:
    """Compute (s, S) reorder rules and target stock levels for each (Product No, Store).

    Formulas:
      - Normal quantile: z = Phi^{-1}(target_service_level)
      - Lead-time demand: mu_L = daily_expected_demand * L
      - Lead-time uncertainty: sigma_L = (demand_std / sqrt(7)) * sqrt(L)
      - Safety stock: SS = max(z * sigma_L, 0.5)
      - Reorder point: s = ceil(mu_L + SS)  (guarantees s >= 1)
      - Annual holding cost: H = annual_holding_cost_rate * unit_cost
      - Annual demand: D_ann = 365 * daily_expected_demand
      - EOQ: ceil(sqrt(2 * D_ann * K / H))
      - Order lot size: Q = max(EOQ, MOQ)
      - Order-up-to level: S = s + Q  (guarantees S > s)
      - Target stock: SS + Q / 2

    Args:
        forecast_df: Forecast DataFrame with ['Product No', 'Store', 'daily_expected_demand', 'demand_std'].
        onhand_df: Daily on-hand DataFrame containing ['Product No', 'Store', 'unit_cost'].
        config: Policy configuration container with explicit assumptions.

    Returns:
        DataFrame matching the schema of artifacts/policy.parquet.
    """
    logger.info("Computing (s, S) inventory policy for %d pairs...", len(forecast_df))

    # 1. Extract the latest cost that is actually present for each pair.  The
    # input is expected to be ordered by date when a date column is supplied.
    cost_columns = ["Product No", "Store", "unit_cost"]
    if "date" in onhand_df.columns:
        costs = (
            onhand_df[cost_columns + ["date"]].copy()
            .assign(date=lambda frame: pd.to_datetime(frame["date"]))
            .sort_values("date")
            .dropna(subset=["unit_cost"])
            .drop_duplicates(["Product No", "Store"], keep="last")
            .drop(columns="date")
        )
    else:
        costs = (
            onhand_df[cost_columns]
            .dropna(subset=["unit_cost"])
            .drop_duplicates(["Product No", "Store"], keep="last")
            .copy()
        )

    merged = forecast_df.merge(costs, on=["Product No", "Store"], how="left", validate="one_to_one")
    merged["unit_cost"] = merged["unit_cost"].astype("float64")
    usable_cost = np.isfinite(merged["unit_cost"].to_numpy(float)) & (merged["unit_cost"].to_numpy(float) > 0)

    # 2. Extract operational parameters
    L = float(config.supplier_lead_time_days)
    sl = float(config.target_service_level)
    r = float(config.annual_holding_cost_rate)
    k_line = float(config.reorder_cost_line_item)
    moq = float(config.min_order_quantity)

    daily_demand = merged["daily_expected_demand"].to_numpy(dtype=np.float64)
    weekly_std = merged["demand_std"].to_numpy(dtype=np.float64)
    unit_cost_arr = merged["unit_cost"].to_numpy(dtype=np.float64)

    # 3-6. Compute core (s, S) policy vectors via the shared single-source-of-truth function.
    vectors = compute_policy_vectors(
        mu_arr=daily_demand,
        std_arr=weekly_std,
        # Keep vector dimensions valid while unavailable rows are masked
        # below.  No fabricated cost is ever emitted or used in a decision.
        unit_costs=np.where(usable_cost, unit_cost_arr, 1.0),
        lead_time_days=L,
        target_service_level=sl,
        holding_cost_rate=r,
        k_line=k_line,
        moq=moq,
        stocking_threshold=config.stocking_demand_threshold,
    )
    safety_stock = vectors["safety_stock"]
    reorder_point_s = vectors["reorder_point_s"]
    order_qty_q = vectors["order_qty_q"]
    order_up_to_S = vectors["order_up_to_S"]
    target_stock = vectors["target_stock"]
    for values in (safety_stock, reorder_point_s, order_qty_q, order_up_to_S, target_stock):
        values[~usable_cost] = np.nan
    is_stocked = vectors["is_stocked"].copy()
    is_stocked[~usable_cost] = False

    # 7. Construct output DataFrame with explicit parameters recorded
    result = pd.DataFrame(
        {
            "Product No": merged["Product No"],
            "Store": merged["Store"],
            "reorder_point_s": reorder_point_s.astype("float64"),
            "order_up_to_S": order_up_to_S.astype("float64"),
            "safety_stock": safety_stock.astype("float64"),
            "order_qty_q": order_qty_q.astype("float64"),
            "target_stock": target_stock.astype("float64"),
            "unit_cost": merged["unit_cost"],
            "daily_expected_demand": merged["daily_expected_demand"],
            "lead_time_days": config.supplier_lead_time_days,
            "target_service_level": config.target_service_level,
            "annual_holding_rate": config.annual_holding_cost_rate,
            "reorder_cost": config.reorder_cost_fixed,
            "min_order_qty": config.min_order_quantity,
            "is_stocked": is_stocked,
            "policy_status": np.where(usable_cost, "available", "unavailable_missing_cost"),
            "cost_assumption": np.where(usable_cost, "latest valid pair cost", "unavailable"),
        }
    )

    logger.info(
        "Policy computed: %d rows. Reorder point range: [%.0f, %.0f], Order-up-to range: [%.0f, %.0f].",
        len(result),
        reorder_point_s.min(),
        reorder_point_s.max(),
        order_up_to_S.min(),
        order_up_to_S.max(),
    )

    return result[list(config.policy_columns)]
