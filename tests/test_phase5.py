"""Test suite for Phase 5: Historical Walk-Forward Simulation.

Verifies all requirements and invariants mandated by PLAN.md:
  - test_phase5_walkforward: simulation consumes exactly 328 days with zero lookahead.
  - test_phase5_nonneg: simulated on-hand is never negative.
  - test_phase5_baseline_repro: observed policy metrics reproduce known audit figures within tolerance.
  - test_phase5_service_guard: optimized service level >= target service level - 5pts.
  - test_phase5_artifacts_completeness: simulation_report.md and simulation_results.parquet valid.
  - test_phase5_synthetic_walkforward_unit: isolated unit test of pipeline ordering logic.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.simulation.config import DEFAULT_SIMULATION_CONFIG, SimulationConfig
from src.simulation.baseline import evaluate_observed_historical_baseline
from src.simulation.engine import run_walkforward_simulation
from src.simulation.sensitivity import recompute_policy_for_scenario
from src.simulation.validator import (
    validate_walkforward,
    validate_non_negativity,
    validate_baseline_reproduction,
    validate_service_level_guard,
    validate_ordering_cost_netting,
    validate_unified_service_level,
)


@pytest.fixture(scope="module")
def preprocessed_arrays():
    """Load baseline datasets and compute preprocessed arrays."""
    onhand_df = pd.read_parquet(
        DEFAULT_SIMULATION_CONFIG.daily_onhand_parquet_path,
        columns=["Product No", "Store", "date", "qty_onhand", "unit_cost"],
    )
    demand_df = pd.read_parquet(
        DEFAULT_SIMULATION_CONFIG.demand_parquet_path,
        columns=["Product No", "Store", "date", "observed_demand", "unconstrained_demand"],
    )
    baseline_metrics, arrays = evaluate_observed_historical_baseline(
        onhand_df, demand_df, DEFAULT_SIMULATION_CONFIG
    )
    return baseline_metrics, arrays


@pytest.fixture(scope="module")
def default_simulation_run(preprocessed_arrays):
    """Run default walk-forward simulation."""
    baseline_metrics, arrays = preprocessed_arrays
    forecast_df = pd.read_parquet(
        DEFAULT_SIMULATION_CONFIG.project_root / "artifacts" / "forecast.parquet",
        columns=["Product No", "Store", "daily_expected_demand", "demand_std"],
    )
    pair_cols = arrays["pair_columns"]
    unit_costs = arrays["unit_costs"]

    f_lookup = forecast_df.set_index(["Product No", "Store"])
    mu_arr = np.array([f_lookup.loc[p, "daily_expected_demand"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)
    std_arr = np.array([f_lookup.loc[p, "demand_std"] if p in f_lookup.index else 0.0 for p in pair_cols], dtype=np.float32)

    s_arr, S_arr = recompute_policy_for_scenario(
        mu_arr=mu_arr,
        std_arr=std_arr,
        unit_costs=unit_costs,
        lead_time_days=DEFAULT_SIMULATION_CONFIG.default_lead_time_days,
        target_service_level=DEFAULT_SIMULATION_CONFIG.default_service_level,
        holding_cost_rate=DEFAULT_SIMULATION_CONFIG.default_annual_holding_rate,
        stocking_threshold=DEFAULT_SIMULATION_CONFIG.default_stocking_demand_threshold,
        moq=float(DEFAULT_SIMULATION_CONFIG.default_min_order_qty),
    )

    metrics, sim_onhand, sim_sales, audit_stats = run_walkforward_simulation(
        arrays=arrays,
        s_arr=s_arr,
        S_arr=S_arr,
        lead_time_days=DEFAULT_SIMULATION_CONFIG.default_lead_time_days,
        holding_cost_rate=DEFAULT_SIMULATION_CONFIG.default_annual_holding_rate,
        target_service_level=DEFAULT_SIMULATION_CONFIG.default_service_level,
    )

    return metrics, sim_onhand, sim_sales, audit_stats


def test_phase5_walkforward(default_simulation_run):
    """Test that simulation consumes exactly 328 days sequentially."""
    _, _, _, audit_stats = default_simulation_run
    passed, msg, metrics = validate_walkforward(
        audit_stats, expected_days=DEFAULT_SIMULATION_CONFIG.total_days
    )
    assert passed, msg
    assert metrics["days_processed"] == 328


def test_phase5_nonneg(default_simulation_run):
    """Test that simulated on-hand inventory is never negative."""
    _, sim_onhand, _, _ = default_simulation_run
    passed, msg, metrics = validate_non_negativity(sim_onhand)
    assert passed, msg
    assert metrics["negative_values_count"] == 0
    assert metrics["min_onhand_val"] >= 0.0


def test_phase5_baseline_repro(preprocessed_arrays):
    """Test that observed baseline metrics reproduce audit figures within strict 5% tolerance."""
    baseline_metrics, _ = preprocessed_arrays
    passed, msg, metrics = validate_baseline_reproduction(
        baseline_metrics, config=DEFAULT_SIMULATION_CONFIG, tolerance=0.05
    )
    assert passed, msg
    assert metrics["stock_relative_diff"] <= 0.05


def test_phase5_service_guard(default_simulation_run):
    """Test that optimized service level >= target service level - 5pts (>= 90%)."""
    _, _, _, audit_stats = default_simulation_run
    passed, msg, metrics = validate_service_level_guard(
        audit_stats, target_service_level=0.95, margin=0.05
    )
    assert passed, msg
    assert metrics["active_service_level"] >= 0.90


def test_phase5_ordering_cost_netted(preprocessed_arrays, default_simulation_run):
    """Test that ordering cost is non-zero, tracked in TCO, and net economic effect is computed."""
    baseline_metrics, _ = preprocessed_arrays
    default_metrics, _, _, _ = default_simulation_run
    passed, msg, metrics = validate_ordering_cost_netting(baseline_metrics, default_metrics)
    assert passed, msg
    assert metrics["baseline_ordering_cost_eur"] > 0
    assert metrics["optimized_ordering_cost_eur"] > 0
    assert metrics["baseline_tco_eur"] > 0
    assert metrics["optimized_tco_eur"] > 0


def test_phase5_unified_service_level(preprocessed_arrays, default_simulation_run):
    """Test that unified active in-stock service level is reported for both policies."""
    baseline_metrics, _ = preprocessed_arrays
    default_metrics, _, _, _ = default_simulation_run
    passed, msg, metrics = validate_unified_service_level(baseline_metrics, default_metrics)
    assert passed, msg
    assert metrics["baseline_active_service_level"] >= 0.90
    assert metrics["optimized_active_service_level"] >= 0.95


def test_phase5_artifacts_completeness():
    """Test that simulation_report.md and simulation_results.parquet exist and are valid."""
    report_path = DEFAULT_SIMULATION_CONFIG.simulation_report_path
    results_path = DEFAULT_SIMULATION_CONFIG.simulation_results_parquet_path

    assert report_path.exists(), f"Report missing at {report_path}"
    assert results_path.exists(), f"Results missing at {results_path}"

    # Verify report content
    report_text = report_path.read_text()
    assert "Headline Result" in report_text
    assert "Head-to-Head Comparison" in report_text
    assert "Full 27-Scenario Sensitivity Sweep Matrix" in report_text

    # Verify parquet results
    df_results = pd.read_parquet(results_path)
    assert len(df_results) == 27
    assert "capital_released_pct" in df_results.columns
    assert "active_service_level" in df_results.columns
    assert "net_economic_savings_eur" in df_results.columns


def test_phase5_synthetic_walkforward_unit():
    """Unit test walk-forward replenishment pipeline on synthetic fixture data."""
    # 2 pairs, 5 days, L = 2 days
    arrays = {
        "pivot_demand": np.array([[1.0, 0.0], [1.0, 2.0], [0.0, 1.0], [2.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        "pivot_onhand": np.array([[2.0, 2.0], [1.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]], dtype=np.float32),
        "unit_costs": np.array([10.0, 20.0], dtype=np.float32),
        "first_idx_arr": np.array([0, 0], dtype=np.int32),
        "last_idx_arr": np.array([4, 4], dtype=np.int32),
    }
    s = np.array([1.0, 1.0], dtype=np.float32)
    S = np.array([3.0, 3.0], dtype=np.float32)

    metrics, onhand_hist, sales_hist, audit = run_walkforward_simulation(
        arrays=arrays,
        s_arr=s,
        S_arr=S,
        lead_time_days=2,
        holding_cost_rate=0.20,
        target_service_level=0.95,
    )

    assert audit["days_processed"] == 5
    assert (onhand_hist >= 0.0).all()
    assert metrics.total_sales_units > 0
