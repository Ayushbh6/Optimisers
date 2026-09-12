import pandas as pd
import numpy as np

from src.forecast.asof import build_asof_forecast_snapshot, evaluate_forecast_benchmarks
from src.forecast.models import croston_forecast, tsb_forecast


def _hierarchy() -> pd.DataFrame:
    return pd.DataFrame({
        "Product No": ["A", "B"],
        "Product Division": ["D", "D"],
        "Product Subcategory": ["SC", "SC"],
    })


def test_croston_uses_completed_intervals():
    rate, _ = croston_forecast(np.array([2.0, 0.0, 2.0]), alpha=1.0)
    assert rate == 1.0


def test_tsb_first_period_is_not_future_informed():
    first_rate, _ = tsb_forecast(np.array([2.0]), alpha=0.1, beta=0.1)
    extended_rate, _ = tsb_forecast(np.array([2.0, 0.0]), alpha=0.1, beta=0.1)
    assert first_rate == 2.0
    assert extended_rate < first_rate


def test_asof_snapshot_ignores_future_purchase_mutation():
    history = pd.DataFrame({
        "Product No": ["A"] * 15,
        "Store": ["S"] * 15,
        "date": pd.date_range("2025-06-02", periods=15, freq="D"),
        "gross_purchase_units": [1.0] * 14 + [999.0],
    })
    cutoff = pd.Timestamp("2025-06-15")
    base = build_asof_forecast_snapshot(history.iloc[:14], _hierarchy(), cutoff, demand_column="gross_purchase_units")
    mutated = build_asof_forecast_snapshot(history, _hierarchy(), cutoff, demand_column="gross_purchase_units")
    pd.testing.assert_frame_equal(base, mutated)


def test_asof_snapshot_excludes_incomplete_week():
    history = pd.DataFrame({
        "Product No": ["A"] * 8,
        "Store": ["S"] * 8,
        "date": pd.date_range("2025-06-02", periods=8, freq="D"),
        "gross_purchase_units": [1.0] * 7 + [1000.0],
    })
    result = build_asof_forecast_snapshot(history, _hierarchy(), pd.Timestamp("2025-06-09"), demand_column="gross_purchase_units")
    assert result["history_days"].iloc[0] == 8
    assert result["weekly_expected_demand"].iloc[0] < 100.0


def test_asof_snapshot_excludes_partial_leading_calendar_week():
    dates = pd.date_range("2025-06-03", periods=12)
    history = pd.DataFrame({
        "Product No": ["A"] * len(dates), "Store": ["S"] * len(dates),
        "date": dates, "estimated_demand": [1.0] * len(dates),
    })
    result = build_asof_forecast_snapshot(history, _hierarchy(), pd.Timestamp("2025-06-14"))
    assert result.empty


def test_dated_hierarchy_is_resolved_at_cutoff():
    dates = pd.date_range("2025-06-02", periods=7)
    history = pd.DataFrame({
        "Product No": ["A"] * 7, "Store": ["S"] * 7,
        "date": dates, "estimated_demand": [1.0] * 7,
    })
    hierarchy = pd.DataFrame({
        "Product No": ["A", "A"], "Product Division": ["old", "new"],
        "Product Subcategory": ["old-sc", "new-sc"],
        "effective_date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01")],
    })
    result = build_asof_forecast_snapshot(history, hierarchy, pd.Timestamp("2025-06-08"))
    assert result["aggregate_level"].iloc[0] == "Product Subcategory x Store"


def test_benchmark_reports_observed_and_estimated_targets_separately():
    dates = pd.date_range("2025-06-02", periods=21)
    history = pd.DataFrame({
        "Product No": ["A"] * len(dates), "Store": ["S"] * len(dates),
        "date": dates, "estimated_demand": [2.0] * len(dates),
        "gross_purchase_units": [1.0] * len(dates),
    })
    detail, summary = evaluate_forecast_benchmarks(
        history, _hierarchy(), pd.date_range("2025-06-16", "2025-06-22")
    )
    assert set(summary["target"]) == {"observed_purchases", "estimated_demand"}
    assert len(detail) == 7
    assert (detail["target_date"] >= pd.Timestamp("2025-06-16")).all()
