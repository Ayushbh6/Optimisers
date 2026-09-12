"""Statistical models for intermittent demand forecasting (Croston and TSB).

Provides explainable, mathematically sound baseline algorithms specifically engineered
for slow-moving and intermittent retail inventory.
"""

from typing import Dict, Tuple
import numpy as np


def croston_forecast(
    series: np.ndarray,
    alpha: float = 0.1,
) -> Tuple[float, float]:
    """Fit Croston's intermittent demand model and project expected rate and uncertainty.

    Decomposes demand into demand sizes (z) and inter-arrival intervals (p):
      z_t = alpha * y_t + (1 - alpha) * z_{t-1}   (when y_t > 0)
      p_t = alpha * q_t + (1 - alpha) * p_{t-1}   (when y_t > 0)
      expected_demand = z_T / p_T

    Args:
        series: 1D numpy array of non-negative demand values over sequential time periods.
        alpha: Smoothing parameter for size and interval updates (0 < alpha <= 1).

    Returns:
        Tuple of (expected_demand_rate: float, residual_std: float).
    """
    n = len(series)
    if n == 0 or np.sum(series) == 0:
        return 0.0, 0.0

    nonzero_indices = np.where(series > 0)[0]
    if len(nonzero_indices) == 0:
        return 0.0, 0.0

    # The first non-zero value starts the size estimate.  The first observed
    # interval is not a completed waiting time, so it must not be used as one.
    first_idx = nonzero_indices[0]
    z = float(series[first_idx])
    p = 1.0
    periods_since_demand = 0

    fitted = np.zeros(n, dtype=np.float64)

    for t in range(n):
        if t < first_idx:
            fitted[t] = 0.0
            continue

        fitted[t] = z / p if p > 0 else z

        if t == first_idx:
            continue
        if series[t] > 0:
            completed_interval = periods_since_demand + 1
            z = alpha * series[t] + (1.0 - alpha) * z
            p = alpha * completed_interval + (1.0 - alpha) * p
            periods_since_demand = 0
        else:
            periods_since_demand += 1

    expected_rate = max(0.0, float(z / p)) if p > 0 else 0.0
    residuals = series[first_idx:] - fitted[first_idx:]
    residual_std = float(np.sqrt(np.mean(residuals**2))) if len(residuals) > 0 else 0.0

    return expected_rate, residual_std


def tsb_forecast(
    series: np.ndarray,
    alpha: float = 0.1,
    beta: float = 0.1,
) -> Tuple[float, float]:
    """Fit Teunter-Syntetos-Babai (TSB) model for intermittent demand.

    Updates demand probability P_t in every period and demand size z_t on positive periods:
      P_t = beta * (1 if y_t > 0 else 0) + (1 - beta) * P_{t-1}
      z_t = alpha * y_t + (1 - alpha) * z_{t-1}   (if y_t > 0, else z_{t-1})
      expected_demand = P_T * z_T

    Args:
        series: 1D array of demand over time.
        alpha: Smoothing parameter for demand size.
        beta: Smoothing parameter for demand probability.

    Returns:
        Tuple of (expected_demand_rate: float, residual_std: float).
    """
    n = len(series)
    if n == 0 or np.sum(series) == 0:
        return 0.0, 0.0

    nonzero_indices = np.where(series > 0)[0]
    if len(nonzero_indices) == 0:
        return 0.0, 0.0

    first_idx = nonzero_indices[0]
    z = float(series[first_idx])
    # Start at the observed demand probability, not a value informed by a
    # later test period.  The update below then learns one period at a time.
    p = 1.0 if first_idx == 0 else 0.0

    fitted = np.zeros(n, dtype=np.float64)

    for t in range(n):
        fitted[t] = p * z
        is_nonzero = 1.0 if series[t] > 0 else 0.0
        p = beta * is_nonzero + (1.0 - beta) * p
        if series[t] > 0:
            z = alpha * series[t] + (1.0 - alpha) * z

    expected_rate = max(0.0, float(p * z))
    residuals = series - fitted
    residual_std = float(np.sqrt(np.mean(residuals**2)))

    return expected_rate, residual_std


def fit_predict_demand(
    series: np.ndarray,
    method: str = "tsb",
    alpha: float = 0.1,
    beta: float = 0.1,
) -> Dict[str, float]:
    """Unified forecast interface with point prediction and uncertainty intervals.

    Args:
        series: 1D historical demand time series.
        method: 'tsb' (default) or 'croston'.
        alpha: Smoothing parameter for demand size.
        beta: Smoothing parameter for demand probability (TSB only).

    Returns:
        Dict with keys:
          'expected_demand', 'demand_std', 'lower_bound_95', 'upper_bound_95', 'method'
    """
    if method == "croston":
        expected_rate, std_err = croston_forecast(series, alpha=alpha)
    else:
        expected_rate, std_err = tsb_forecast(series, alpha=alpha, beta=beta)

    # This is a normal-approximation diagnostic, not a calibrated promise.
    lower_95 = max(0.0, expected_rate - 1.96 * std_err)
    upper_95 = max(expected_rate, expected_rate + 1.96 * std_err)

    return {
        "expected_demand": float(expected_rate),
        "demand_std": float(std_err),
        "lower_bound_95": float(lower_95),
        "upper_bound_95": float(upper_95),
        "method": method,
    }
