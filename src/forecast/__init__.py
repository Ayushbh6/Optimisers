"""Phase 3: Hierarchical Intermittent Demand Forecasting Module.

Exports core forecasting models, hierarchical aggregation, top-down disaggregation,
hold-out evaluation, and validation suites.
"""

from src.forecast.config import ForecastConfig, DEFAULT_FORECAST_CONFIG
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

__all__ = [
    "ForecastConfig",
    "DEFAULT_FORECAST_CONFIG",
    "croston_forecast",
    "tsb_forecast",
    "fit_predict_demand",
    "prepare_weekly_demand_series",
    "compute_sku_demand_shares",
    "disaggregate_forecast",
    "evaluate_holdout_performance",
    "validate_no_leakage",
    "validate_disaggregation",
    "validate_mase_baseline",
    "validate_non_negativity",
    "validate_prediction_intervals",
]
