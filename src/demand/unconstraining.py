"""Hierarchical unconstrained demand estimation engine.

Corrects for stockout censoring by imputing true unconstrained demand on days
where on-hand inventory was zero, using an explainable multi-tier fallback hierarchy:
  1. SKU x Store in-stock mean
  2. SKU Global (enterprise-wide) in-stock mean
  3. Subcategory x Store in-stock mean
  4. Subcategory Global in-stock mean
  5. Zero floor
"""

import logging
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from src.demand.config import DemandConfig, DEFAULT_DEMAND_CONFIG

logger = logging.getLogger(__name__)


def extract_product_hierarchy(
    raw_inventory_df: pd.DataFrame,
) -> pd.DataFrame:
    """Extract deterministic SKU-to-hierarchy mapping.

    Args:
        raw_inventory_df: Raw inventory or sales DataFrame containing hierarchy columns.

    Returns:
        DataFrame with unique ['Product No', 'Product Division', 'Product Category', 'Product Subcategory', 'Product Segment'].
    """
    cols = [
        "Product No",
        "Product Division",
        "Product Category",
        "Product Subcategory",
        "Product Segment",
    ]
    hierarchy = raw_inventory_df[cols].drop_duplicates().reset_index(drop=True)
    logger.info("Extracted deterministic hierarchy for %d unique products.", len(hierarchy))
    return hierarchy


def compute_in_stock_demand_rates(
    aligned_df: pd.DataFrame,
    hierarchy_df: pd.DataFrame,
    config: DemandConfig = DEFAULT_DEMAND_CONFIG,
) -> Dict[str, pd.DataFrame]:
    """Compute baseline daily demand rates from in-stock (uncensored) observation windows.

    Negative daily sales (customer returns) are floored at 0.0 so returns do not artificially
    depress positive consumer purchasing velocity.

    Args:
        aligned_df: DataFrame containing daily records with 'is_censored' flag.
        hierarchy_df: SKU hierarchy mapping.
        config: Demand configuration containing minimum in-stock days thresholds.

    Returns:
        Dictionary of baseline rate tables across the hierarchy tiers.
    """
    logger.info("Computing in-stock demand rates across hierarchy tiers...")

    # Focus strictly on in-stock (uncensored) observation days
    in_stock = aligned_df[~aligned_df["is_censored"]].copy()
    in_stock["clean_demand"] = np.maximum(in_stock["observed_demand"], 0.0)

    # Attach hierarchy
    in_stock = in_stock.merge(
        hierarchy_df[["Product No", "Product Subcategory"]],
        on="Product No",
        how="left",
    )

    # Level 1: SKU x Store rate
    sku_store = (
        in_stock.groupby(["Product No", "Store"])["clean_demand"]
        .agg(n_days="count", rate="mean")
        .reset_index()
    )
    sku_store_valid = sku_store[sku_store["n_days"] >= config.min_in_stock_days_sku_store]

    # Level 2: SKU Global rate
    sku_global = (
        in_stock.groupby("Product No")["clean_demand"]
        .agg(n_days="count", rate="mean")
        .reset_index()
    )
    sku_global_valid = sku_global[sku_global["n_days"] >= config.min_in_stock_days_sku_global]

    # Level 3: Subcategory x Store rate
    subcat_store = (
        in_stock.groupby(["Product Subcategory", "Store"])["clean_demand"]
        .agg(n_days="count", rate="mean")
        .reset_index()
    )
    subcat_store_valid = subcat_store[subcat_store["n_days"] >= config.min_in_stock_days_subcat_store]

    # Level 4: Subcategory Global rate
    subcat_global = (
        in_stock.groupby("Product Subcategory")["clean_demand"]
        .agg(n_days="count", rate="mean")
        .reset_index()
    )

    logger.info(
        "Computed in-stock rates: SKU-Store (%d pairs), SKU-Global (%d SKUs), Subcat-Store (%d), Subcat-Global (%d).",
        len(sku_store_valid),
        len(sku_global_valid),
        len(subcat_store_valid),
        len(subcat_global),
    )

    return {
        "sku_store": sku_store_valid,
        "sku_global": sku_global_valid,
        "subcat_store": subcat_store_valid,
        "subcat_global": subcat_global,
    }


def estimate_unconstrained_demand(
    aligned_df: pd.DataFrame,
    hierarchy_df: pd.DataFrame,
    config: DemandConfig = DEFAULT_DEMAND_CONFIG,
) -> pd.DataFrame:
    """Reconstruct unconstrained demand series for all (Product No, Store, date) records.

    For uncensored days (qty_onhand > 0):
      unconstrained_demand = max(0.0, observed_demand)
      imputation_method = 'observed'

    For censored days (qty_onhand == 0):
      imputed_rate = fallback_hierarchy(SKU-Store -> SKU-Global -> Subcat-Store -> Subcat-Global -> 0.0)
      unconstrained_demand = max(observed_demand, imputed_rate, 0.0)
      imputation_method = name of fallback tier that supplied the rate

    Args:
        aligned_df: Aligned on-hand and daily sales DataFrame.
        hierarchy_df: Product hierarchy mapping DataFrame.
        config: Demand configuration container.

    Returns:
        DataFrame with columns:
          ['Product No', 'Store', 'date', 'observed_demand', 'unconstrained_demand', 'is_censored', 'imputation_method']
    """
    logger.info("Executing unconstrained demand estimation over %d records...", len(aligned_df))

    rates = compute_in_stock_demand_rates(aligned_df, hierarchy_df, config)

    # Initialize unconstrained demand and imputation method
    result = aligned_df.copy()
    result["unconstrained_demand"] = np.maximum(result["observed_demand"], 0.0)
    result["imputation_method"] = "observed"

    # Identify censored rows
    censored_mask = result["is_censored"].to_numpy()
    censored_indices = np.where(censored_mask)[0]
    num_censored = len(censored_indices)

    if num_censored == 0:
        logger.info("No censored rows found. Returning aligned DataFrame with observed values.")
        return result[list(config.demand_columns)]

    censored_df = result.iloc[censored_indices][["Product No", "Store"]].copy()
    censored_df = censored_df.merge(
        hierarchy_df[["Product No", "Product Subcategory"]],
        on="Product No",
        how="left",
    )

    # Multi-tier fallback joins
    # Level 1: SKU x Store
    m1 = censored_df[["Product No", "Store"]].merge(
        rates["sku_store"][["Product No", "Store", "rate"]],
        on=["Product No", "Store"],
        how="left",
    )["rate"].to_numpy()

    # Level 2: SKU Global
    m2 = censored_df[["Product No"]].merge(
        rates["sku_global"][["Product No", "rate"]],
        on="Product No",
        how="left",
    )["rate"].to_numpy()

    # Level 3: Subcategory x Store
    m3 = censored_df[["Product Subcategory", "Store"]].merge(
        rates["subcat_store"][["Product Subcategory", "Store", "rate"]],
        on=["Product Subcategory", "Store"],
        how="left",
    )["rate"].to_numpy()

    # Level 4: Subcategory Global
    m4 = censored_df[["Product Subcategory"]].merge(
        rates["subcat_global"][["Product Subcategory", "rate"]],
        on="Product Subcategory",
        how="left",
    )["rate"].to_numpy()

    # Resolve tier values and method names
    tier1_mask = ~np.isnan(m1)
    tier2_mask = (~tier1_mask) & (~np.isnan(m2))
    tier3_mask = (~tier1_mask) & (~tier2_mask) & (~np.isnan(m3))
    tier4_mask = (~tier1_mask) & (~tier2_mask) & (~tier3_mask) & (~np.isnan(m4))
    tier5_mask = (~tier1_mask) & (~tier2_mask) & (~tier3_mask) & (~tier4_mask)

    imputed_values = np.zeros(num_censored, dtype=np.float64)
    imputed_values[tier1_mask] = m1[tier1_mask]
    imputed_values[tier2_mask] = m2[tier2_mask]
    imputed_values[tier3_mask] = m3[tier3_mask]
    imputed_values[tier4_mask] = m4[tier4_mask]
    imputed_values[tier5_mask] = 0.0

    imputed_methods = np.empty(num_censored, dtype=object)
    imputed_methods[tier1_mask] = "sku_store_in_stock_mean"
    imputed_methods[tier2_mask] = "sku_global_in_stock_mean"
    imputed_methods[tier3_mask] = "subcategory_store_in_stock_mean"
    imputed_methods[tier4_mask] = "subcategory_global_in_stock_mean"
    imputed_methods[tier5_mask] = "zero_floor"

    # Enforce unconstrained_demand = max(observed_demand, imputed_values, 0.0)
    censored_observed = result.iloc[censored_indices]["observed_demand"].to_numpy()
    final_censored_demand = np.maximum(censored_observed, imputed_values)
    final_censored_demand = np.maximum(final_censored_demand, 0.0)

    # Assign back to result DataFrame
    result.iloc[censored_indices, result.columns.get_loc("unconstrained_demand")] = final_censored_demand
    result.iloc[censored_indices, result.columns.get_loc("imputation_method")] = imputed_methods

    logger.info(
        "Demand estimation complete. Imputation breakdown:\n%s",
        result["imputation_method"].value_counts().to_string(),
    )

    return result[list(config.demand_columns)]
