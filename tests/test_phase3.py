"""Test suite for Phase 3: Demand Forecasting.

Verifies all requirements and invariants mandated by PLAN.md:
  - test_phase3_no_leakage: strict training boundary without temporal overlap.
  - test_phase3_disaggregation: SKU forecasts sum exactly to aggregate forecasts.
  - test_phase3_baseline: hold-out MASE < 1.0 on Scholar Footwear (beats naive).
  - test_phase3_nonneg: all point forecasts and bounds >= 0.
  - test_phase3_prediction_intervals: valid bounds (lower <= expected <= upper).
  - test_phase3_synthetic_intermittent_models: unit test for Croston and TSB math.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.demand.unconstraining import extract_product_hierarchy
from src.forecast.config import DEFAULT_FORECAST_CONFIG, ForecastConfig
from src.forecast.models import croston_forecast, tsb_forecast, fit_predict_demand
from src.forecast.aggregation import prepare_weekly_demand_series
from src.forecast.disaggregation import compute_sku_demand_shares, disaggregate_forecast
from src.forecast.evaluator import evaluate_holdout_performance
from src.forecast.validator import (
    validate_no_leakage,
    validate_disaggregation,
    validate_mase_baseline,
    validate_non_negativity,
    validate_prediction_intervals,
)


@pytest.fixture(scope="module")
def forecast_df():
    """Load the generated forecast.parquet artifact."""
    artifact_path = DEFAULT_FORECAST_CONFIG.forecast_parquet_path
    assert artifact_path.exists(), f"Artifact not found at {artifact_path}. Run build_forecast first."
    return pd.read_parquet(artifact_path)


@pytest.fixture(scope="module")
def hierarchy_df():
    """Load the product hierarchy."""
    inv = pd.read_csv(
        DEFAULT_FORECAST_CONFIG.inventory_csv_path,
        usecols=[
            "Product No",
            "Product Division",
            "Product Category",
            "Product Subcategory",
            "Product Segment",
        ],
    )
    return extract_product_hierarchy(inv)


@pytest.fixture(scope="module")
def weekly_aggregates(hierarchy_df):
    """Compute weekly aggregates."""
    demand = pd.read_parquet(DEFAULT_FORECAST_CONFIG.demand_parquet_path)
    return prepare_weekly_demand_series(demand, hierarchy_df, DEFAULT_FORECAST_CONFIG)


def test_phase3_no_leakage(weekly_aggregates):
    """Test that train and test windows are strictly chronological with 0 overlap."""
    weekly_agg, _ = weekly_aggregates
    weeks = sorted(weekly_agg["week"].unique())
    n_train = int(len(weeks) * DEFAULT_FORECAST_CONFIG.train_ratio)
    train_weeks = set(weeks[:n_train])
    test_weeks = set(weeks[n_train:])

    passed, msg, metrics = validate_no_leakage(train_weeks, test_weeks)
    assert passed, msg
    assert metrics["intersection_count"] == 0
    assert metrics["train_weeks_count"] == 33
    assert metrics["test_weeks_count"] == 15


def test_phase3_disaggregation(forecast_df, hierarchy_df):
    """Test that SKU forecasts reconcile back to aggregate forecasts within tolerance."""
    # Reconstruct aggregate forecasts by summing SKUs
    merged = forecast_df.merge(hierarchy_df[["Product No", "Product Subcategory"]], on="Product No")
    subcat_sums = merged.groupby(["Product Subcategory", "Store"])["weekly_expected_demand"].sum().reset_index()
    subcat_sums.rename(columns={"weekly_expected_demand": "aggregate_expected_demand"}, inplace=True)

    passed, msg, metrics = validate_disaggregation(
        sku_forecast_df=forecast_df,
        aggregate_forecast_df=subcat_sums,
        hierarchy_df=hierarchy_df,
        tolerance=1e-4,
    )
    assert passed, msg
    assert metrics["violations"] == 0


def test_phase3_baseline(weekly_aggregates):
    """Test that hold-out MASE < 1.0 (beats naive baseline) on Scholar Footwear."""
    weekly_agg, _ = weekly_aggregates
    eval_metrics = evaluate_holdout_performance(
        weekly_aggregate_df=weekly_agg,
        target_division="Scholar Footwear",
        method="croston",
        config=DEFAULT_FORECAST_CONFIG,
    )

    passed, msg, _ = validate_mase_baseline(eval_metrics)
    assert passed, msg
    assert eval_metrics["global_mase"] < 1.0
    assert eval_metrics["median_mase"] < 1.0


def test_phase3_nonneg(forecast_df):
    """Test that all forecasts and bounds are non-negative."""
    passed, msg, metrics = validate_non_negativity(forecast_df)
    assert passed, msg
    assert metrics["negative_weekly_demand"] == 0
    assert metrics["negative_daily_demand"] == 0
    assert metrics["negative_std"] == 0


def test_phase3_prediction_intervals(forecast_df):
    """Test that lower_bound_95 <= weekly_expected_demand <= upper_bound_95 everywhere."""
    passed, msg, metrics = validate_prediction_intervals(forecast_df)
    assert passed, msg
    assert metrics["lower_bound_violations"] == 0
    assert metrics["upper_bound_violations"] == 0


def test_phase3_synthetic_intermittent_models():
    """Unit test Croston and TSB implementations on synthetic benchmark data."""
    # Intermittent demand series: demand occurs only at t=2, t=5, t=9
    ts = np.array([0, 0, 4, 0, 0, 6, 0, 0, 0, 5], dtype=np.float64)

    # 1. Test Croston
    croston_rate, croston_std = croston_forecast(ts, alpha=0.1)
    assert croston_rate > 0.0
    assert croston_std > 0.0

    # 2. Test TSB
    tsb_rate, tsb_std = tsb_forecast(ts, alpha=0.1, beta=0.1)
    assert tsb_rate > 0.0
    assert tsb_std > 0.0

    # 3. Test zero series
    zero_ts = np.zeros(10, dtype=np.float64)
    z_rate, z_std = croston_forecast(zero_ts)
    assert z_rate == 0.0
    assert z_std == 0.0
