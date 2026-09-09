"""Sensitivity sweep engine across multi-parameter grid combinations.

Sweeps across:
  - Lead times: {5, 10, 15} days
  - Target service levels: {90%, 95%, 98%}
  - Annual holding cost rates: {15%, 20%, 25%}
Total = 27 scenario evaluations.
"""

import logging
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.engine import run_walkforward_simulation
from src.simulation.metrics import SimulationMetrics
from src.policy.engine import compute_policy_vectors

logger = logging.getLogger(__name__)


def recompute_policy_for_scenario(
    mu_arr: np.ndarray,
    std_arr: np.ndarray,
    unit_costs: np.ndarray,
    lead_time_days: int,
    target_service_level: float,
    holding_cost_rate: float,
    stocking_threshold: float = 0.004,
    k_line: float = 2.0,
    moq: float = 5.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Recompute (s, S) policy arrays for a specific sensitivity scenario.

    Delegates to the shared single-source-of-truth policy maths in
    `src.policy.engine.compute_policy_vectors`, so the simulation can never drift
    from the Phase 4 policy artifact.

    Args:
        mu_arr: Daily expected demand vector.
        std_arr: Demand standard deviation vector.
        unit_costs: Wholesale costs per pair.
        lead_time_days: Scenario lead time.
        target_service_level: Scenario service level.
        holding_cost_rate: Scenario holding cost rate.
        stocking_threshold: Minimum daily demand velocity to stock shelf.
        k_line: Marginal order cost per line item.
        moq: Minimum order quantity (MOQ = 5).

    Returns:
        Tuple of (s_arr, S_arr).
    """
    vectors = compute_policy_vectors(
        mu_arr=mu_arr,
        std_arr=std_arr,
        unit_costs=unit_costs,
        lead_time_days=lead_time_days,
        target_service_level=target_service_level,
        holding_cost_rate=holding_cost_rate,
        k_line=k_line,
        moq=moq,
        stocking_threshold=stocking_threshold,
    )
    s_arr = vectors["reorder_point_s"].astype(np.float32)
    S_arr = vectors["order_up_to_S"].astype(np.float32)
    return s_arr, S_arr


def run_sensitivity_sweep(
    arrays: Dict[str, Any],
    forecast_df: pd.DataFrame,
    baseline_metrics: SimulationMetrics,
    config: SimulationConfig = DEFAULT_SIMULATION_CONFIG,
) -> pd.DataFrame:
    """Execute full 27-scenario sensitivity sweep with Total Cost of Ownership netting.

    Args:
        arrays: Preprocessed simulation arrays.
        forecast_df: Forecast DataFrame.
        baseline_metrics: Metrics from observed historical baseline.
        config: Simulation configuration container.

    Returns:
        DataFrame containing scenario results and comparisons against baseline.
    """
    logger.info("Initiating 27-scenario sensitivity sweep with TCO accounting...")
    records: List[Dict[str, Any]] = []

    pair_cols = arrays["pair_columns"]
    unit_costs = arrays["unit_costs"]
    base_inv = baseline_metrics.avg_inventory_value_eur
    base_tco = baseline_metrics.total_cost_of_ownership_eur

    # Pre-extract forecast vectors once
    f_lookup = forecast_df.set_index(["Product No", "Store"])
    mu_arr = np.array([f_lookup.loc[p, "daily_expected_demand"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)
    std_arr = np.array([f_lookup.loc[p, "demand_std"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)

    scenario_id = 1
    for L in config.lead_time_grid:
        for SL in config.service_level_grid:
            for r in config.holding_rate_grid:
                # 1. Compute scenario policy (instant vector calculation with MOQ = 5)
                s_arr, S_arr = recompute_policy_for_scenario(
                    mu_arr=mu_arr,
                    std_arr=std_arr,
                    unit_costs=unit_costs,
                    lead_time_days=L,
                    target_service_level=SL,
                    holding_cost_rate=r,
                    stocking_threshold=config.default_stocking_demand_threshold,
                    moq=float(config.default_min_order_qty),
                )

                # 2. Run simulation
                metrics, _, _, audit_stats = run_walkforward_simulation(
                    arrays=arrays,
                    s_arr=s_arr,
                    S_arr=S_arr,
                    lead_time_days=L,
                    holding_cost_rate=r,
                    target_service_level=SL,
                    reorder_cost_fixed=config.default_reorder_cost_fixed,
                )

                # 3. Compute delta against baseline
                cap_saved = base_inv - metrics.avg_inventory_value_eur
                cap_saved_pct = (cap_saved / base_inv) * 100.0 if base_inv > 0 else 0.0
                net_savings = base_tco - metrics.total_cost_of_ownership_eur

                records.append(
                    {
                        "scenario_id": scenario_id,
                        "lead_time_days": L,
                        "target_service_level": SL,
                        "holding_rate": r,
                        "avg_inventory_val_eur": metrics.avg_inventory_value_eur,
                        "baseline_inventory_val_eur": base_inv,
                        "capital_released_eur": cap_saved,
                        "capital_released_pct": cap_saved_pct,
                        "active_service_level": metrics.active_in_stock_service_level,
                        "fill_rate": metrics.fill_rate_service_level,
                        "turnover": metrics.inventory_turnover,
                        "days_sales_inventory": metrics.days_sales_inventory,
                        "holding_cost_eur": metrics.holding_cost_eur,
                        "ordering_cost_eur": metrics.ordering_cost_eur,
                        "total_tco_eur": metrics.total_cost_of_ownership_eur,
                        "net_economic_savings_eur": net_savings,
                        "total_orders": metrics.total_orders_count,
                    }
                )
                scenario_id += 1

    df_results = pd.DataFrame(records)
    logger.info(
        "Sensitivity sweep complete: 27 scenarios simulated.\n"
        "  - Capital released range: [%.1f%%, %.1f%%]\n"
        "  - Net economic savings range: [€%.0f, €%.0f]\n"
        "  - Realized active service level range: [%.1f%%, %.1f%%]",
        df_results["capital_released_pct"].min(),
        df_results["capital_released_pct"].max(),
        df_results["net_economic_savings_eur"].min(),
        df_results["net_economic_savings_eur"].max(),
        df_results["active_service_level"].min() * 100,
        df_results["active_service_level"].max() * 100,
    )

    return df_results
