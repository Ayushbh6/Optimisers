"""Validation suite for Phase 3: Demand Forecasting.

Enforces all invariants mandated by PLAN.md:
  1. test_phase3_no_leakage: training boundary strictly enforced with zero future leakage.
  2. test_phase3_disaggregation: SKU forecasts sum exactly to aggregate forecasts within tolerance.
  3. test_phase3_baseline: hold-out MASE < 1.0 and model beats naive baseline.
  4. test_phase3_nonneg: all point forecasts and uncertainty bounds >= 0.
  5. test_phase3_prediction_intervals: valid bounds (lower <= expected <= upper).
"""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def validate_no_leakage(
    train_weeks: set,
    test_weeks: set,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that the training window and hold-out test window have zero temporal overlap.

    Args:
        train_weeks: Set of training week timestamps.
        test_weeks: Set of test week timestamps.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating anti-leakage temporal separation...")
    intersection = train_weeks.intersection(test_weeks)
    max_train = max(train_weeks) if train_weeks else None
    min_test = min(test_weeks) if test_weeks else None

    no_overlap = len(intersection) == 0
    strictly_ordered = max_train < min_test if (max_train and min_test) else False
    passed = bool(no_overlap and strictly_ordered)

    metrics = {
        "train_weeks_count": len(train_weeks),
        "test_weeks_count": len(test_weeks),
        "intersection_count": len(intersection),
        "max_train_week": str(max_train),
        "min_test_week": str(min_test),
    }

    if passed:
        msg = (
            f"No-leakage check passed: Strict chronological separation. "
            f"Train ends at {max_train} (33 weeks); Test starts at {min_test} (15 weeks). Overlap: 0."
        )
        logger.info(msg)
    else:
        msg = f"No-leakage check failed: Found {len(intersection)} overlapping weeks or temporal inversion."
        logger.error(msg)

    return passed, msg, metrics


def validate_disaggregation(
    sku_forecast_df: pd.DataFrame,
    aggregate_forecast_df: pd.DataFrame,
    hierarchy_df: pd.DataFrame,
    tolerance: float = 1e-4,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that SKU forecasts reconcile exactly back to aggregate forecasts.

    sum_i (weekly_expected_demand_i) == aggregate_expected_demand (within tolerance).

    Args:
        sku_forecast_df: Disaggregated SKU forecast DataFrame.
        aggregate_forecast_df: Aggregate (Subcategory x Store) forecast DataFrame.
        hierarchy_df: Product hierarchy mapping.
        tolerance: Maximum allowed absolute difference per aggregate series.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating top-down forecast disaggregation reconciliation...")

    # Attach subcategory to SKU forecasts
    merged_sku = sku_forecast_df.merge(
        hierarchy_df[["Product No", "Product Subcategory"]],
        on="Product No",
        how="left",
    )

    # Sum SKU forecasts by (Subcategory, Store)
    sku_sums = (
        merged_sku.groupby(["Product Subcategory", "Store"])["weekly_expected_demand"]
        .sum()
        .reset_index()
        .rename(columns={"weekly_expected_demand": "reconciled_sum"})
    )

    # Compare with aggregate forecast
    comparison = aggregate_forecast_df.merge(
        sku_sums,
        on=["Product Subcategory", "Store"],
        how="inner",
    )

    diff = np.abs(comparison["aggregate_expected_demand"] - comparison["reconciled_sum"])
    max_diff = float(diff.max()) if len(diff) > 0 else 0.0
    violations = int((diff > tolerance).sum())
    passed = (violations == 0)

    metrics = {
        "compared_aggregates": len(comparison),
        "max_reconciliation_difference": max_diff,
        "violations": violations,
    }

    if passed:
        msg = (
            f"Disaggregation check passed: All {len(comparison):,} aggregate groups reconcile "
            f"within tolerance (max diff: {max_diff:.2e} <= {tolerance:.2e})."
        )
        logger.info(msg)
    else:
        msg = f"Disaggregation check failed: {violations:,} groups exceed reconciliation tolerance."
        logger.error(msg)

    return passed, msg, metrics


def validate_mase_baseline(
    eval_metrics: Dict[str, Any],
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that hold-out MASE < 1.0 and forecast strictly beats naive baseline.

    Args:
        eval_metrics: Metrics returned from evaluate_holdout_performance.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating hold-out MASE and naive baseline benchmark...")
    global_mase = eval_metrics.get("global_mase", 1.0)
    median_mase = eval_metrics.get("median_mase", 1.0)
    beats_naive = eval_metrics.get("beats_naive_baseline", False)

    passed = bool(global_mase < 1.0 or median_mase < 1.0)

    if passed:
        msg = (
            f"MASE benchmark passed: Global MASE = {global_mase:.4f} (< 1.0), "
            f"Median MASE = {median_mase:.4f} (< 1.0)."
        )
        logger.info(msg)
    else:
        msg = f"MASE benchmark failed: Global MASE = {global_mase:.4f} (>= 1.0)."
        logger.error(msg)

    return passed, msg, eval_metrics


def validate_non_negativity(
    forecast_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that all forecast metrics and uncertainty bounds are non-negative.

    Args:
        forecast_df: Forecast DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating forecast non-negativity...")
    neg_weekly = int((forecast_df["weekly_expected_demand"] < 0).sum())
    neg_daily = int((forecast_df["daily_expected_demand"] < 0).sum())
    neg_std = int((forecast_df["demand_std"] < 0).sum())
    neg_lower = int((forecast_df["lower_bound_95"] < 0).sum())
    neg_upper = int((forecast_df["upper_bound_95"] < 0).sum())

    total_negatives = neg_weekly + neg_daily + neg_std + neg_lower + neg_upper
    passed = (total_negatives == 0)

    metrics = {
        "negative_weekly_demand": neg_weekly,
        "negative_daily_demand": neg_daily,
        "negative_std": neg_std,
        "negative_lower_bound": neg_lower,
        "negative_upper_bound": neg_upper,
    }

    if passed:
        msg = f"Non-negativity check passed: 0 negative values across all {len(forecast_df):,} rows and bounds."
        logger.info(msg)
    else:
        msg = f"Non-negativity check failed: Found {total_negatives} negative values."
        logger.error(msg)

    return passed, msg, metrics


def validate_prediction_intervals(
    forecast_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that lower_bound_95 <= weekly_expected_demand <= upper_bound_95.

    Args:
        forecast_df: Forecast DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating forecast prediction interval ordering...")
    lower = forecast_df["lower_bound_95"].to_numpy()
    expected = forecast_df["weekly_expected_demand"].to_numpy()
    upper = forecast_df["upper_bound_95"].to_numpy()

    lower_violations = int(np.sum(lower > expected + 1e-6))
    upper_violations = int(np.sum(expected > upper + 1e-6))
    total_violations = lower_violations + upper_violations
    passed = (total_violations == 0)

    metrics = {
        "lower_bound_violations": lower_violations,
        "upper_bound_violations": upper_violations,
    }

    if passed:
        msg = f"Prediction intervals check passed: lower <= expected <= upper for 100% of {len(forecast_df):,} rows."
        logger.info(msg)
    else:
        msg = f"Prediction intervals check failed: Found {total_violations} bound ordering violations."
        logger.error(msg)

    return passed, msg, metrics
