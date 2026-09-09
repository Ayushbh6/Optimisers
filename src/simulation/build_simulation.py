"""Command-line pipeline runner for Phase 5: Walk-Forward Historical Simulation.

Executes baseline reproduction, runs 328-day chronological simulation, conducts
a 27-scenario sensitivity sweep, validates all invariants, and writes:
  - artifacts/simulation_report.md
  - artifacts/simulation_results.parquet

Usage:
    python -m src.simulation.build_simulation
"""

import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.baseline import evaluate_observed_historical_baseline
from src.simulation.engine import run_walkforward_simulation
from src.simulation.sensitivity import run_sensitivity_sweep, recompute_policy_for_scenario
from src.simulation.report import generate_simulation_report
from src.simulation.validator import (
    validate_walkforward,
    validate_non_negativity,
    validate_baseline_reproduction,
    validate_service_level_guard,
    validate_ordering_cost_netting,
    validate_unified_service_level,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("build_simulation")


def run_phase5_pipeline(config: SimulationConfig = DEFAULT_SIMULATION_CONFIG) -> Path:
    """Execute end-to-end Phase 5 simulation pipeline.

    Args:
        config: Simulation configuration container.

    Returns:
        Path to the written artifacts/simulation_report.md file.

    Raises:
        RuntimeError: If any Phase 5 validation checks fail.
        FileNotFoundError: If input artifacts are missing.
    """
    start_time = time.time()
    logger.info("=== Starting Phase 5 Pipeline: Walk-Forward Historical Simulation ===")

    # 1. Verify input artifacts
    for p, name in [
        (config.daily_onhand_parquet_path, "daily_onhand"),
        (config.demand_parquet_path, "demand"),
        (config.policy_parquet_path, "policy"),
    ]:
        if not p.exists():
            raise FileNotFoundError(f"Input artifact missing at {p}. Run previous phases first.")

    # 2. Ingest datasets
    logger.info("Loading inputs...")
    onhand_df = pd.read_parquet(
        config.daily_onhand_parquet_path,
        columns=["Product No", "Store", "date", "qty_onhand", "unit_cost"],
    )
    demand_df = pd.read_parquet(
        config.demand_parquet_path,
        columns=["Product No", "Store", "date", "observed_demand", "unconstrained_demand"],
    )
    forecast_df = pd.read_parquet(
        config.project_root / "artifacts" / "forecast.parquet",
        columns=["Product No", "Store", "daily_expected_demand", "demand_std"],
    )

    # 3. Evaluate historical observed baseline
    baseline_metrics, arrays = evaluate_observed_historical_baseline(onhand_df, demand_df, config)

    # 4. Recompute default policy arrays
    pair_cols = arrays["pair_columns"]
    unit_costs = arrays["unit_costs"]
    f_lookup = forecast_df.set_index(["Product No", "Store"])
    mu_arr = np.array([f_lookup.loc[p, "daily_expected_demand"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)
    std_arr = np.array([f_lookup.loc[p, "demand_std"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)

    s_arr, S_arr = recompute_policy_for_scenario(
        mu_arr=mu_arr,
        std_arr=std_arr,
        unit_costs=unit_costs,
        lead_time_days=config.default_lead_time_days,
        target_service_level=config.default_service_level,
        holding_cost_rate=config.default_annual_holding_rate,
        stocking_threshold=config.default_stocking_demand_threshold,
        moq=float(config.default_min_order_qty),
    )

    # 5. Run default walk-forward simulation
    logger.info("Running default walk-forward simulation across 328 days...")
    default_metrics, sim_onhand, sim_sales, default_audit = run_walkforward_simulation(
        arrays=arrays,
        s_arr=s_arr,
        S_arr=S_arr,
        lead_time_days=config.default_lead_time_days,
        holding_cost_rate=config.default_annual_holding_rate,
        target_service_level=config.default_service_level,
        reorder_cost_fixed=config.default_reorder_cost_fixed,
    )

    # 6. Run 27-scenario sensitivity sweep
    sensitivity_df = run_sensitivity_sweep(
        arrays=arrays,
        forecast_df=forecast_df,
        baseline_metrics=baseline_metrics,
        config=config,
    )

    # 7. Validate all invariants
    v_walk, msg_walk, _ = validate_walkforward(default_audit, expected_days=config.total_days)
    v_nonneg, msg_nonneg, _ = validate_non_negativity(sim_onhand)
    v_base, msg_base, _ = validate_baseline_reproduction(baseline_metrics, config=config, tolerance=0.05)
    v_guard, msg_guard, _ = validate_service_level_guard(
        default_audit, target_service_level=config.default_service_level, margin=0.05
    )
    v_order_net, msg_order_net, _ = validate_ordering_cost_netting(baseline_metrics, default_metrics)
    v_uni_sl, msg_uni_sl, _ = validate_unified_service_level(baseline_metrics, default_metrics)

    logger.info("[✓] WALKFORWARD_COMPLETENESS: %s", msg_walk)
    logger.info("[✓] NON_NEGATIVITY: %s", msg_nonneg)
    logger.info("[✓] BASELINE_REPRODUCTION: %s", msg_base)
    logger.info("[✓] SERVICE_LEVEL_GUARD: %s", msg_guard)
    logger.info("[✓] ORDERING_COST_NETTING: %s", msg_order_net)
    logger.info("[✓] UNIFIED_SERVICE_LEVEL: %s", msg_uni_sl)

    if not (v_walk and v_nonneg and v_base and v_guard and v_order_net and v_uni_sl):
        raise RuntimeError("Phase 5 pipeline aborted: Validation checks failed.")

    # 8. Write artifacts
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing sensitivity results to %s ...", config.simulation_results_parquet_path)
    sensitivity_df.to_parquet(config.simulation_results_parquet_path, index=False, engine="pyarrow")

    logger.info("Writing simulation report to %s ...", config.simulation_report_path)
    generate_simulation_report(
        baseline_metrics=baseline_metrics,
        default_metrics=default_metrics,
        default_audit=default_audit,
        sensitivity_df=sensitivity_df,
        output_path=config.simulation_report_path,
    )

    elapsed = time.time() - start_time
    logger.info("=== Phase 5 Pipeline Completed Successfully in %.2fs ===", elapsed)
    logger.info("Report path: %s", config.simulation_report_path)
    logger.info("Sensitivity results path: %s", config.simulation_results_parquet_path)

    return config.simulation_report_path


if __name__ == "__main__":
    try:
        run_phase5_pipeline()
    except Exception as exc:
        logger.critical("Fatal error during Phase 5 pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
