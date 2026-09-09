"""Sales aggregation and stockout censoring detection."""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def aggregate_daily_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw sales transactions to daily net units per (Product No, Store, date).

    Net units = sum of 'Qty Sold' (returns are naturally included as negative quantities).

    Args:
        sales_df: Raw sales ledger with columns 'Product No', 'Store',
                  'Transaction Date', and 'Qty Sold'.

    Returns:
        DataFrame with columns ['Product No', 'Store', 'date', 'observed_demand'].
    """
    logger.info("Aggregating daily sales transactions to (Product No, Store, date)...")
    sales = sales_df.copy()
    if "date" not in sales.columns:
        sales["date"] = pd.to_datetime(sales["Transaction Date"])
    elif not pd.api.types.is_datetime64_any_dtype(sales["date"]):
        sales["date"] = pd.to_datetime(sales["date"])

    daily_sales = (
        sales.groupby(["Product No", "Store", "date"], as_index=False)["Qty Sold"]
        .sum()
        .rename(columns={"Qty Sold": "observed_demand"})
    )
    daily_sales["observed_demand"] = daily_sales["observed_demand"].astype("float64")
    logger.info(
        "Aggregated %d raw transactions into %d daily product-store sales dates.",
        len(sales_df),
        len(daily_sales),
    )
    return daily_sales


def compute_active_lifespans(
    onhand_df: pd.DataFrame,
    daily_sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute active assortment lifespan boundaries (first and last active dates) per (Product No, Store).

    An active date is defined as any date with positive on-hand inventory (qty_onhand > 0)
    or positive consumer sales activity (observed_demand > 0).

    Args:
        onhand_df: Daily on-hand DataFrame.
        daily_sales_df: Daily sales DataFrame.

    Returns:
        DataFrame with ['Product No', 'Store', 'first_active', 'last_active'].
    """
    active_onhand = onhand_df[onhand_df["qty_onhand"] > 0]
    active_sales = daily_sales_df[daily_sales_df["observed_demand"] > 0]

    first_onhand = active_onhand.groupby(["Product No", "Store"])["date"].min()
    last_onhand = active_onhand.groupby(["Product No", "Store"])["date"].max()
    first_sales = active_sales.groupby(["Product No", "Store"])["date"].min()
    last_sales = active_sales.groupby(["Product No", "Store"])["date"].max()

    first_active = pd.concat([first_onhand, first_sales], axis=1).min(axis=1).rename("first_active")
    last_active = pd.concat([last_onhand, last_sales], axis=1).max(axis=1).rename("last_active")

    spans = pd.concat([first_active, last_active], axis=1).reset_index()
    return spans


def identify_censoring(
    aligned_df: pd.DataFrame,
) -> pd.Series:
    """Identify stockout days where shelf inventory is zero strictly within active product lifecycles.

    A day is flagged as censored (lost sales) if and only if:
      1. qty_onhand == 0 (shelf was empty)
      2. date >= first_active AND date < last_active (product is still in active assortment,
         with future inventory or sales occurring later)

    Zero-stock days after last_active represent discontinued/retired products with zero demand.

    Args:
        aligned_df: DataFrame with ['date', 'qty_onhand', 'first_active', 'last_active'].

    Returns:
        Boolean Series where True indicates a mid-lifecycle stockout day.
    """
    has_zero_stock = (aligned_df["qty_onhand"] == 0)
    in_active_lifecycle = (
        (aligned_df["date"] >= aligned_df["first_active"]) &
        (aligned_df["date"] < aligned_df["last_active"])
    )
    return has_zero_stock & in_active_lifecycle


def align_sales_and_inventory(
    onhand_df: pd.DataFrame,
    daily_sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """Align daily sales to the contiguous daily on-hand grid and flag mid-lifecycle stockouts.

    Days without sales activity are filled with 0.0 observed demand.
    Censored days are flagged strictly for mid-lifecycle stockout periods.

    Args:
        onhand_df: Authoritative daily on-hand table with ['Product No', 'Store', 'date', 'qty_onhand'].
        daily_sales_df: Aggregated daily sales with ['Product No', 'Store', 'date', 'observed_demand'].

    Returns:
        Aligned DataFrame with ['Product No', 'Store', 'date', 'qty_onhand', 'observed_demand', 'is_censored'].
    """
    logger.info("Aligning %d daily on-hand records with daily sales...", len(onhand_df))
    aligned = onhand_df[["Product No", "Store", "date", "qty_onhand"]].merge(
        daily_sales_df[["Product No", "Store", "date", "observed_demand"]],
        on=["Product No", "Store", "date"],
        how="left",
    )
    aligned["observed_demand"] = aligned["observed_demand"].fillna(0.0).astype("float64")

    # Compute active lifespans and identify mid-lifecycle stockouts
    lifespans = compute_active_lifespans(onhand_df, daily_sales_df)
    aligned = aligned.merge(lifespans, on=["Product No", "Store"], how="left")

    aligned["is_censored"] = identify_censoring(aligned)
    aligned.drop(columns=["first_active", "last_active"], inplace=True)

    logger.info(
        "Alignment complete: %d total rows, %d mid-lifecycle stockouts (%.2f%%).",
        len(aligned),
        aligned["is_censored"].sum(),
        aligned["is_censored"].mean() * 100,
    )
    return aligned
