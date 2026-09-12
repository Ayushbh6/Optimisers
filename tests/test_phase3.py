"""Synthetic checks for causal intermittent forecasting."""

import numpy as np
import pandas as pd

from src.forecast.aggregation import prepare_weekly_demand_series
from src.forecast.asof import build_asof_forecast_snapshot
from src.forecast.models import fit_predict_demand


def test_croston_counts_completed_intervals():
    assert fit_predict_demand(np.array([2.0, 0.0, 2.0]), method="croston", alpha=1.0)["expected_demand"] == 1.0


def test_tsb_initial_probability_has_no_future_sale():
    # The first sale is only learned after its day; with beta=.1 the final
    # occurrence probability is .1 and the expected value is .4.
    assert fit_predict_demand(np.array([0.0, 0.0, 4.0]), method="tsb", alpha=0.1, beta=0.1)["expected_demand"] == 0.4


def test_week_starts_monday_and_incomplete_week_is_excluded():
    dates = pd.date_range("2025-06-02", periods=8)
    demand = pd.DataFrame({"Product No": ["p"] * 8, "Store": ["s"] * 8, "date": dates, "estimated_demand": [1.0] * 8, "unconstrained_demand": [1.0] * 8})
    hierarchy = pd.DataFrame({"Product No": ["p"], "Product Division": ["d"], "Product Subcategory": ["c"]})
    weekly, _ = prepare_weekly_demand_series(demand, hierarchy)
    assert list(weekly["week"].dt.weekday.unique()) == [0]
    assert build_asof_forecast_snapshot(demand, hierarchy, pd.Timestamp("2025-06-07")).empty


def test_forecast_snapshot_records_its_information_cutoff():
    dates = pd.date_range("2025-06-02", periods=14)
    demand = pd.DataFrame({"Product No": ["p"] * 14, "Store": ["s"] * 14, "date": dates, "estimated_demand": [1.0] * 14})
    hierarchy = pd.DataFrame({"Product No": ["p"], "Product Division": ["d"], "Product Subcategory": ["c"]})
    result = build_asof_forecast_snapshot(demand, hierarchy, pd.Timestamp("2025-06-15"))
    assert (result.information_cutoff == pd.Timestamp("2025-06-15")).all()
    assert (result.forecast_start_date == pd.Timestamp("2025-06-16")).all()
