"""Historical baseline evaluation module.

Evaluates the actual observed historical timeline using uniform metric calculators
to verify reproduction of known audit figures (~$2.4M average standing stock, ~2.71x turnover).
"""

import logging
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.metrics import SimulationMetrics, compute_simulation_metrics

logger = logging.getLogger(__name__)


def evaluate_observed_historical_baseline(
    onhand_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    config: SimulationConfig = DEFAULT_SIMULATION_CONFIG,
) -> Tuple[SimulationMetrics, Dict[str, np.ndarray]]:
    """Compute performance metrics for the historical observed inventory timeline.

    Args:
        onhand_df: Authoritative daily on-hand DataFrame.
        demand_df: Demand matrix DataFrame.
        config: Simulation configuration container.

    Returns:
        Tuple of (SimulationMetrics instance, preprocessed_arrays dictionary).
    """
    logger.info("Evaluating observed historical baseline across %d pairs and %d days...",
                onhand_df["Product No"].nunique() * onhand_df["Store"].nunique(),
                onhand_df["date"].nunique())

    # 1. Align and pivot matrices to shape (n_days, n_pairs)
    dates = sorted(onhand_df["date"].unique())
    pairs = onhand_df[["Product No", "Store"]].drop_duplicates().sort_values(["Product No", "Store"]).reset_index(drop=True)
    n_days = len(dates)
    n_pairs = len(pairs)

    logger.info("Pivoting daily on-hand, sales, and demand arrays (%d x %d)...", n_days, n_pairs)

    # Fast indexed arrays
    merged = onhand_df[["Product No", "Store", "date", "qty_onhand", "unit_cost"]].merge(
        demand_df[["Product No", "Store", "date", "observed_demand", "unconstrained_demand"]],
        on=["Product No", "Store", "date"],
        how="inner",
    )

    # Pivot to (n_days, n_pairs)
    pivot_onhand = (
        merged.pivot(index="date", columns=["Product No", "Store"], values="qty_onhand")
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )

    # Observed sales: non-negative units sold
    pivot_sales = (
        merged.pivot(index="date", columns=["Product No", "Store"], values="observed_demand")
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )
    pivot_sales = np.maximum(pivot_sales, 0.0)

    # Unconstrained demand
    pivot_demand = (
        merged.pivot(index="date", columns=["Product No", "Store"], values="unconstrained_demand")
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )

    # Unit costs per pair (aligned to column ordering)
    pair_cols = merged.pivot(index="date", columns=["Product No", "Store"], values="unit_cost").columns
    cost_lookup = (
        onhand_df.groupby(["Product No", "Store"])["unit_cost"]
        .first()
        .to_dict()
    )
    costs = np.array([cost_lookup.get((p, s), 25.0) for p, s in pair_cols], dtype=np.float32)

    # Vectorized active lifespan calculation
    has_pos = (pivot_onhand > 0)
    first_idx_arr = np.where(has_pos.any(axis=0), has_pos.argmax(axis=0), n_days).astype(np.int32)
    last_idx_arr = np.where(has_pos.any(axis=0), n_days - 1 - has_pos[::-1].argmax(axis=0), n_days).astype(np.int32)

    # 2. Active lifecycle in-stock service level
    # An active day is when the product is within its active lifecycle (first_idx <= t <= last_idx)
    t_grid = np.arange(n_days)[:, None]
    active_matrix = (t_grid >= first_idx_arr[None, :]) & (t_grid <= last_idx_arr[None, :])
    total_active_days = int(np.sum(active_matrix))
    active_in_stock_days = int(np.sum(active_matrix & (pivot_onhand > 0)))

    # 3. Compute baseline metrics
    baseline_metrics = compute_simulation_metrics(
        daily_onhand_history=pivot_onhand,
        daily_sales_history=pivot_sales,
        daily_demand_history=pivot_demand,
        unit_costs=costs,
        holding_cost_rate=config.default_annual_holding_rate,
        reorder_cost_fixed=config.default_reorder_cost_fixed,
        orders_count=config.baseline_replenishment_orders,
        active_in_stock_days=active_in_stock_days,
        total_active_days=total_active_days,
    )

    logger.info(
        "Historical Observed Baseline:\n"
        "  - Standing Inventory Value: €%.2f (Audit reference: ~$2.4M - $2.65M)\n"
        "  - Annualized COGS: €%.2f (Audit reference: ~$6.5M)\n"
        "  - Turnover: %.2fx (Audit reference: ~2.71x)\n"
        "  - Days Sales of Inventory (DSI): %.1f days (Audit reference: ~135 days)\n"
        "  - Active In-Stock Service Level: %.2f%%\n"
        "  - Fill Rate: %.2f%%\n"
        "  - Holding Cost: €%.2f\n"
        "  - Ordering Cost (%d deliveries @ €50): €%.2f\n"
        "  - Total Cost of Ownership: €%.2f",
        baseline_metrics.avg_inventory_value_eur,
        baseline_metrics.annual_cogs_eur,
        baseline_metrics.inventory_turnover,
        baseline_metrics.days_sales_inventory,
        baseline_metrics.active_in_stock_service_level * 100,
        baseline_metrics.fill_rate_service_level * 100,
        baseline_metrics.holding_cost_eur,
        config.baseline_replenishment_orders,
        baseline_metrics.ordering_cost_eur,
        baseline_metrics.total_cost_of_ownership_eur,
    )

    arrays = {
        "dates": np.array(dates),
        "pair_columns": pair_cols,
        "pivot_onhand": pivot_onhand,
        "pivot_sales": pivot_sales,
        "pivot_demand": pivot_demand,
        "unit_costs": costs,
        "first_idx_arr": first_idx_arr,
        "last_idx_arr": last_idx_arr,
    }

    return baseline_metrics, arrays
