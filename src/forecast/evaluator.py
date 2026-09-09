"""Hold-out evaluation engine for demand forecasting.

Strictly enforces anti-leakage boundaries by fitting models strictly on training weeks
and evaluating on a held-out temporal window using Mean Absolute Scaled Error (MASE)
and Mean Absolute Error (MAE) compared against a Naive persistence baseline.
"""

import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.forecast.config import ForecastConfig, DEFAULT_FORECAST_CONFIG
from src.forecast.models import croston_forecast, tsb_forecast

logger = logging.getLogger(__name__)


def evaluate_holdout_performance(
    weekly_aggregate_df: pd.DataFrame,
    target_division: str = "Scholar Footwear",
    method: str = "croston",
    config: ForecastConfig = DEFAULT_FORECAST_CONFIG,
) -> Dict[str, Any]:
    """Evaluate hold-out forecasting accuracy against Naive baseline with zero leakage.

    Splits the weekly time series into:
      - Training window: First ~70% of chronological weeks (strictly <= train_cutoff)
      - Held-out test window: Final ~30% of weeks

    Computes:
      - Total Absolute Error for Model vs. Naive
      - Portfolio MASE (Mean Absolute Scaled Error)
      - Median MASE across individual series

    Args:
        weekly_aggregate_df: Weekly aggregate demand DataFrame.
        target_division: Division to evaluate (defaults to 'Scholar Footwear').
        method: Forecasting algorithm ('croston' or 'tsb').
        config: Configuration containing train/holdout split ratios and hyperparameters.

    Returns:
        Dict containing performance metrics and validation flags.
    """
    logger.info(
        "Evaluating hold-out forecast accuracy on %s using method='%s'...",
        target_division,
        method,
    )

    # 1. Temporal boundary definition (strictly chronological)
    weeks = sorted(weekly_aggregate_df["week"].unique())
    n_weeks = len(weeks)
    n_train = int(n_weeks * config.train_ratio)
    train_weeks = set(weeks[:n_train])
    test_weeks = set(weeks[n_train:])
    train_cutoff = weeks[n_train - 1]
    test_start = weeks[n_train]

    logger.info(
        "Temporal split: %d total weeks (%s to %s). "
        "Train: %d weeks (up to %s). Test: %d weeks (from %s).",
        n_weeks,
        weeks[0].strftime("%Y-%m-%d"),
        weeks[-1].strftime("%Y-%m-%d"),
        n_train,
        train_cutoff.strftime("%Y-%m-%d"),
        len(test_weeks),
        test_start.strftime("%Y-%m-%d"),
    )

    # Filter for target division
    div_df = weekly_aggregate_df[weekly_aggregate_df["Product Division"] == target_division]
    series_groups = div_df.groupby(["Product Subcategory", "Store"])

    total_model_abs_err = 0.0
    total_naive_abs_err = 0.0
    total_in_sample_scale_err = 0.0
    individual_mases: List[float] = []

    for (subcat, store), group in series_groups:
        # Reconstruct complete chronological vector over all weeks
        ts_dict = dict(zip(group["week"], group["weekly_demand"]))
        full_ts = np.array([ts_dict.get(w, 0.0) for w in weeks], dtype=np.float64)

        train_ts = full_ts[:n_train]
        test_ts = full_ts[n_train:]

        # Skip series with zero activity everywhere
        if np.sum(train_ts) == 0 and np.sum(test_ts) == 0:
            continue

        # Fit model strictly on in-sample training data (no lookahead leakage)
        if method == "croston":
            pred_rate, _ = croston_forecast(train_ts, alpha=config.alpha)
        else:
            pred_rate, _ = tsb_forecast(train_ts, alpha=config.alpha, beta=config.beta)

        # Naive baseline: last observed in-sample train value
        naive_pred = train_ts[-1] if len(train_ts) > 0 else 0.0

        model_err = np.sum(np.abs(test_ts - pred_rate))
        naive_err = np.sum(np.abs(test_ts - naive_pred))

        total_model_abs_err += float(model_err)
        total_naive_abs_err += float(naive_err)

        # In-sample scale for MASE
        diff = np.abs(np.diff(train_ts))
        in_sample_err_sum = float(np.sum(diff))
        total_in_sample_scale_err += in_sample_err_sum

        if in_sample_err_sum > 1e-4:
            scale_step = in_sample_err_sum / (len(train_ts) - 1)
            mae_test = float(model_err / len(test_ts))
            individual_mases.append(mae_test / scale_step)

    # Global Portfolio MASE calculation
    test_len = len(test_weeks)
    train_steps = n_train - 1
    norm_factor = test_len / train_steps if train_steps > 0 else 1.0
    global_mase = (
        float(total_model_abs_err / (total_in_sample_scale_err * norm_factor))
        if total_in_sample_scale_err > 0
        else 1.0
    )
    median_mase = float(np.median(individual_mases)) if len(individual_mases) > 0 else 1.0
    error_ratio = (
        float(total_model_abs_err / total_naive_abs_err) if total_naive_abs_err > 0 else 1.0
    )

    passed_mase = bool(global_mase < 1.0 or median_mase < 1.0)
    passed_naive = bool(total_model_abs_err < total_naive_abs_err)

    logger.info(
        "Hold-out Evaluation Results for %s:\n"
        "  - Global Portfolio MASE: %.4f (Target: < 1.0, Beats Naive: %s)\n"
        "  - Median Series MASE: %.4f\n"
        "  - Total Test Absolute Error (Model): %.1f\n"
        "  - Total Test Absolute Error (Naive): %.1f\n"
        "  - Relative Error vs Naive: %.4f (%.2f%% lower error than naive)",
        target_division,
        global_mase,
        passed_mase,
        median_mase,
        total_model_abs_err,
        total_naive_abs_err,
        error_ratio,
        (1.0 - error_ratio) * 100,
    )

    return {
        "target_division": target_division,
        "method": method,
        "n_train_weeks": n_train,
        "n_test_weeks": len(test_weeks),
        "train_cutoff": str(train_cutoff),
        "test_start": str(test_start),
        "global_mase": global_mase,
        "median_mase": median_mase,
        "total_model_error": total_model_abs_err,
        "total_naive_error": total_naive_abs_err,
        "error_ratio_vs_naive": error_ratio,
        "passed_mase_threshold": passed_mase,
        "beats_naive_baseline": passed_naive,
    }
