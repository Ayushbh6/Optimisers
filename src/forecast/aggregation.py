"""Temporal and hierarchical aggregation routines for weekly demand series."""

import logging
from typing import Tuple
import pandas as pd

from src.forecast.config import ForecastConfig, DEFAULT_FORECAST_CONFIG

logger = logging.getLogger(__name__)


def prepare_weekly_demand_series(
    demand_df: pd.DataFrame,
    hierarchy_df: pd.DataFrame,
    config: ForecastConfig = DEFAULT_FORECAST_CONFIG,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate unconstrained daily demand into weekly series at both aggregate and SKU levels.

    Args:
        demand_df: Demand DataFrame with ['Product No', 'Store', 'date', 'unconstrained_demand'].
        hierarchy_df: Hierarchy DataFrame with ['Product No', 'Product Division', 'Product Subcategory'].
        config: Forecast configuration container.

    Returns:
        Tuple of (weekly_aggregate_df, weekly_sku_df):
          - weekly_aggregate_df: ['Product Division', 'Product Subcategory', 'Store', 'week', 'weekly_demand']
          - weekly_sku_df: ['Product No', 'Product Subcategory', 'Store', 'week', 'weekly_demand']
    """
    logger.info("Aggregating %d daily records to weekly frequency...", len(demand_df))

    # 1. Attach weekly timestamp (Monday-based start)
    df = demand_df[["Product No", "Store", "date", "unconstrained_demand"]].copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    # Monday--Sunday weeks.  ``W-MON`` represents Tuesday--Monday, which made
    # the old weekly units disagree with the documentation.
    df["week"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")

    # Merge hierarchy
    df = df.merge(
        hierarchy_df[["Product No", "Product Division", "Product Subcategory"]],
        on="Product No",
        how="left",
    )

    # 2. Aggregate to SKU x Store x week
    weekly_sku = (
        df.groupby(["Product No", "Product Subcategory", "Store", "week"], as_index=False)["unconstrained_demand"]
        .sum()
        .rename(columns={"unconstrained_demand": "weekly_demand"})
    )

    # 3. Aggregate to Subcategory x Store x week
    weekly_aggregate = (
        df.groupby(["Product Division", "Product Subcategory", "Store", "week"], as_index=False)["unconstrained_demand"]
        .sum()
        .rename(columns={"unconstrained_demand": "weekly_demand"})
    )

    logger.info(
        "Aggregation complete: %d weekly aggregate points across %d subcat-store series.",
        len(weekly_aggregate),
        weekly_aggregate.groupby(["Product Subcategory", "Store"]).ngroups,
    )

    return weekly_aggregate, weekly_sku
