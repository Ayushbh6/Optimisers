"""Policy snapshots that use a dated, pair-specific cost tape."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.policy.config import PolicyConfig, DEFAULT_POLICY_CONFIG
from src.policy.engine import compute_policy_vectors


def build_asof_policy_snapshot(
    forecast_snapshot: pd.DataFrame,
    cost_as_of: pd.DataFrame,
    config: PolicyConfig = DEFAULT_POLICY_CONFIG,
) -> pd.DataFrame:
    """Turn one as-of forecast into policy rows without inventing a missing cost.

    ``cost_as_of`` must contain one already-known cost per product/store.  A
    missing or non-positive cost makes the recommendation unavailable instead
    of falling back to a fabricated EUR25 value.
    """
    required_forecast = {"Product No", "Store", "daily_expected_demand", "demand_std", "information_cutoff"}
    required_cost = {"Product No", "Store", "unit_cost_as_of"}
    if required_forecast - set(forecast_snapshot.columns):
        raise ValueError("Forecast snapshot misses required policy inputs")
    if required_cost - set(cost_as_of.columns):
        raise ValueError("Cost tape misses required as-of cost inputs")
    forecast = forecast_snapshot.copy()
    # Accept either a pre-resolved as-of tape or dated cost observations.  In
    # the latter case, resolve each pair at its own cutoff and never borrow a
    # value from another pair or from a later date.
    if "date" in cost_as_of.columns:
        dated = cost_as_of[["Product No", "Store", "date", "unit_cost_as_of"]].copy()
        dated["date"] = pd.to_datetime(dated["date"]).dt.normalize()
        forecast["_row"] = np.arange(len(forecast))
        forecast["_cutoff"] = pd.to_datetime(forecast["information_cutoff"]).dt.normalize()
        dated = dated[dated.unit_cost_as_of.notna() & np.isfinite(dated.unit_cost_as_of) & (dated.unit_cost_as_of > 0)]
        candidates = forecast.merge(dated, on=["Product No", "Store"], how="left")
        candidates = candidates[candidates["date"] <= candidates["_cutoff"]]
        latest = candidates.sort_values(["_row", "date"], kind="stable").drop_duplicates("_row", keep="last")
        data = forecast.merge(latest[["_row", "unit_cost_as_of"]], on="_row", how="left", validate="one_to_one").drop(columns=["_row", "_cutoff"])
    else:
        tape = cost_as_of[["Product No", "Store", "unit_cost_as_of"]].copy()
        tape = tape.drop_duplicates(["Product No", "Store"], keep="last")
        data = forecast.merge(tape, on=["Product No", "Store"], how="left", validate="one_to_one").copy()
    usable = data["unit_cost_as_of"].notna() & np.isfinite(data["unit_cost_as_of"]) & (data["unit_cost_as_of"] > 0)
    size = len(data)
    vectors = compute_policy_vectors(
        mu_arr=data["daily_expected_demand"].fillna(0).to_numpy(float),
        std_arr=data["demand_std"].fillna(0).to_numpy(float),
        unit_costs=data["unit_cost_as_of"].where(usable, 1).to_numpy(float),
        lead_time_days=config.supplier_lead_time_days,
        target_service_level=config.target_service_level,
        holding_cost_rate=config.annual_holding_cost_rate,
        k_line=config.reorder_cost_line_item,
        moq=config.min_order_quantity,
        stocking_threshold=config.stocking_demand_threshold,
    )
    for key, values in vectors.items():
        data[key] = values
    for column in ("safety_stock", "reorder_point_s", "order_qty_q", "order_up_to_S", "target_stock"):
        data.loc[~usable, column] = np.nan
    data["stocking_eligible"] = data["is_stocked"]
    data["is_stocked"] = data["is_stocked"] & usable
    data["policy_status"] = np.where(usable, "available", "unavailable_missing_cost")
    data["cost_assumption"] = np.where(usable, "latest valid pair cost at cutoff", "unavailable")
    data["lead_time_days"] = config.supplier_lead_time_days
    data["target_service_level"] = config.target_service_level
    data["annual_holding_rate"] = config.annual_holding_cost_rate
    data["min_order_qty"] = config.min_order_quantity
    return data
