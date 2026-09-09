"""Top-down hierarchical forecast disaggregation engine.

Reconciles aggregate (Subcategory x Store) forecasts down to individual SKU x Store
units using empirical historical demand shares with Laplace smoothing priors.
"""

import logging
import numpy as np
import pandas as pd

from src.forecast.config import ForecastConfig, DEFAULT_FORECAST_CONFIG

logger = logging.getLogger(__name__)


def compute_sku_demand_shares(
    weekly_sku_df: pd.DataFrame,
    laplace_prior: float = 1e-4,
) -> pd.DataFrame:
    """Calculate historical demand proportions for each SKU within its (Subcategory, Store).

    Uses a Laplace prior epsilon so every active SKU receives a strictly positive share:
      share_i = (D_i + eps) / sum_j(D_j + eps)

    Args:
        weekly_sku_df: SKU weekly demand DataFrame.
        laplace_prior: Small positive constant added to avoid zero division / zero share.

    Returns:
        DataFrame with ['Product No', 'Product Subcategory', 'Store', 'demand_share'].
    """
    logger.info("Computing SKU demand shares with Laplace prior (eps=%.1e)...", laplace_prior)

    # 1. Total historical demand per SKU x Store
    sku_totals = (
        weekly_sku_df.groupby(["Product No", "Product Subcategory", "Store"], as_index=False)["weekly_demand"]
        .sum()
        .rename(columns={"weekly_demand": "sku_total_demand"})
    )

    # 2. Total historical demand per Subcategory x Store
    subcat_totals = (
        sku_totals.groupby(["Product Subcategory", "Store"])["sku_total_demand"]
        .transform("sum")
    )
    sku_counts = (
        sku_totals.groupby(["Product Subcategory", "Store"])["Product No"]
        .transform("count")
    )

    # 3. Smoothed share
    numerator = sku_totals["sku_total_demand"] + laplace_prior
    denominator = subcat_totals + (sku_counts * laplace_prior)
    sku_totals["demand_share"] = numerator / denominator

    logger.info("Calculated demand shares for %d (Product No, Store) pairs.", len(sku_totals))
    return sku_totals[["Product No", "Product Subcategory", "Store", "demand_share"]]


def disaggregate_forecast(
    aggregate_forecast_df: pd.DataFrame,
    sku_shares_df: pd.DataFrame,
    config: ForecastConfig = DEFAULT_FORECAST_CONFIG,
) -> pd.DataFrame:
    """Disaggregate aggregate forecasts down to SKU x Store level and construct final schema.

    Reconciles exactly so sum of SKU forecasts equals aggregate forecast:
      weekly_expected_demand_i = demand_share_i * aggregate_expected_demand
      daily_expected_demand_i = weekly_expected_demand_i / 7.0

    Args:
        aggregate_forecast_df: Forecasts at (Product Subcategory, Store) level.
        sku_shares_df: Proportional demand shares per SKU.
        config: Forecast configuration container.

    Returns:
        DataFrame matching the schema of artifacts/forecast.parquet:
          ['Product No', 'Store', 'forecast_horizon_weeks', 'weekly_expected_demand',
           'daily_expected_demand', 'demand_std', 'lower_bound_95', 'upper_bound_95',
           'method', 'aggregate_level']
    """
    logger.info("Disaggregating aggregate forecasts to SKU level...")

    merged = sku_shares_df.merge(
        aggregate_forecast_df,
        on=["Product Subcategory", "Store"],
        how="inner",
    )

    # Expected point forecasts
    merged["weekly_expected_demand"] = (
        merged["demand_share"] * merged["aggregate_expected_demand"]
    ).astype("float64")
    merged["daily_expected_demand"] = (merged["weekly_expected_demand"] / 7.0).astype("float64")

    # Scale standard deviation by square root of share (standard Poisson/sum dispersion)
    merged["demand_std"] = (
        np.sqrt(merged["demand_share"]) * merged["aggregate_demand_std"]
    ).astype("float64")

    # Prediction interval bounds
    merged["lower_bound_95"] = np.maximum(
        0.0,
        merged["weekly_expected_demand"] - 1.96 * merged["demand_std"],
    ).astype("float64")
    merged["upper_bound_95"] = np.maximum(
        merged["weekly_expected_demand"],
        merged["weekly_expected_demand"] + 1.96 * merged["demand_std"],
    ).astype("float64")

    merged["forecast_horizon_weeks"] = config.forecast_horizon_weeks
    merged["aggregate_level"] = config.aggregate_level

    result = merged[list(config.forecast_columns)].copy()
    logger.info("Disaggregation complete: %d SKU-store forecast rows generated.", len(result))
    return result
