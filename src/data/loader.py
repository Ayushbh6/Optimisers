"""Data ingestion and schema validation module for retail sales and inventory ledgers."""

import logging
from typing import Optional
import numpy as np
import pandas as pd

from src.data.config import DEFAULT_CONFIG, DataConfig

logger = logging.getLogger(__name__)


def load_inventory_data(
    config: DataConfig = DEFAULT_CONFIG,
    csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """Load raw inventory ledger, validate columns, and parse interval dates.

    Maps sentinel '9999-12-31' to observation horizon end for interval expansion.

    Args:
        config: System data configuration.
        csv_path: Optional custom path to inventory CSV.

    Returns:
        pd.DataFrame: Cleaned inventory interval records with parsed datetime fields.
    """
    path = csv_path or str(config.inventory_csv_path)
    logger.info("Loading raw inventory ledger from %s", path)
    df = pd.read_csv(path, low_memory=False)

    missing_cols = set(config.inventory_required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Inventory CSV missing required columns: {missing_cols}")

    # Parse interval dates
    df["Start Date"] = pd.to_datetime(df["Start Date"])
    
    # Store raw End Date as sentinel check and create parsed End Date capped at observation horizon
    df["raw_end_date"] = df["End Date"].astype(str)
    capped_end = df["End Date"].replace({config.sentinel_end_date: config.observation_end_date})
    df["End Date_parsed"] = pd.to_datetime(capped_end)

    # Validate interval logic
    if (df["Start Date"] > df["End Date_parsed"]).any():
        invalid_count = (df["Start Date"] > df["End Date_parsed"]).sum()
        raise ValueError(f"Found {invalid_count} inventory rows where Start Date > End Date_parsed")

    return df


def load_sales_data(
    config: DataConfig = DEFAULT_CONFIG,
    csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """Load raw sales ledger, validate columns, and parse transaction dates.

    Args:
        config: System data configuration.
        csv_path: Optional custom path to sales CSV.

    Returns:
        pd.DataFrame: Validated sales transaction records.
    """
    path = csv_path or str(config.sales_csv_path)
    logger.info("Loading raw sales ledger from %s", path)
    df = pd.read_csv(path, low_memory=False)

    missing_cols = set(config.sales_required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Sales CSV missing required columns: {missing_cols}")

    df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")
    if df["Transaction Date"].isna().any():
        raise ValueError("Sales CSV contains invalid Transaction Date values")
    validate_sales_transactions(df)
    return df


def _return_flags(values: pd.Series) -> pd.Series:
    """Convert the source return flag to a strict boolean mask."""
    normalised = values.astype(str).str.strip().str.lower()
    yes = {"1", "1.0", "true", "yes", "y", "return"}
    no = {"0", "0.0", "false", "no", "n"}
    if not normalised.isin(yes | no).all():
        raise ValueError("Sales data contains an invalid Is Return flag")
    return normalised.isin(yes)


def validate_sales_transactions(sales_df: pd.DataFrame) -> None:
    """Reject invalid quantity/return combinations before aggregation.

    A negative non-return and a positive return are source-record errors.  They
    must be fixed or explicitly accounted for by the caller; turning either
    into zero would silently lose physical units and make reconciliation
    impossible.
    """
    if "Qty Sold" not in sales_df.columns:
        raise ValueError("Sales data missing required column: Qty Sold")
    quantity = pd.to_numeric(sales_df["Qty Sold"], errors="coerce")
    invalid = quantity.isna() | ~np.isfinite(quantity)
    if invalid.any():
        count = int(invalid.sum())
        raise ValueError(f"Sales data contains {count} invalid Qty Sold values")
    if (quantity != np.floor(quantity)).any():
        raise ValueError("Qty Sold must contain whole units")
    for key in ("Product No", "Store"):
        if key in sales_df and sales_df[key].isna().any():
            raise ValueError(f"Sales data contains missing {key}")
    if "Is Return" not in sales_df.columns:
        return
    flags = _return_flags(sales_df["Is Return"])
    invalid_non_return = (~flags & (quantity < 0)).sum()
    invalid_return = (flags & (quantity > 0)).sum()
    if invalid_non_return or invalid_return:
        raise ValueError(
            "Sales quantity/return flag mismatch: "
            f"{int(invalid_non_return)} negative non-returns and "
            f"{int(invalid_return)} positive returns"
        )


def aggregate_daily_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sales into gross purchases, returns, and physical net movement.

    ``gross_qty_sold`` is the customer purchase stream used for demand.  Returns
    are kept separately because they do not represent a new customer purchase.
    ``net_qty_sold`` is retained for stock movement only (gross purchases minus
    returned units).  This distinction prevents returns from lowering demand
    while still putting returned units back on the physical shelf.

    Args:
        sales_df: Raw or filtered sales ledger.

    Returns:
        DataFrame with one row per product-store-date and explicit gross,
        returned, and net quantities.
    """
    required = {"Product No", "Store", "Qty Sold"}
    missing = required - set(sales_df.columns)
    if missing:
        raise ValueError(f"Sales data missing required columns: {sorted(missing)}")

    sales = sales_df.copy()
    if "date" not in sales.columns:
        if "Transaction Date" not in sales.columns:
            raise ValueError("Sales data needs either 'date' or 'Transaction Date'.")
        sales["date"] = pd.to_datetime(sales["Transaction Date"])
    else:
        sales["date"] = pd.to_datetime(sales["date"])

    validate_sales_transactions(sales)
    qty = pd.to_numeric(sales["Qty Sold"], errors="raise").astype(float)
    sales["Qty Sold"] = qty
    if "Is Return" in sales.columns:
        is_return = _return_flags(sales["Is Return"])
    else:
        # Synthetic and older exports may not carry the return flag.  Negative
        # quantities are then the only safe return signal.
        is_return = qty < 0

    sales["returned_qty"] = np.where(is_return, np.maximum(-qty, 0.0), 0.0)
    sales["gross_qty_sold"] = np.where(~is_return, np.maximum(qty, 0.0), 0.0)
    sales["net_qty_sold"] = sales["gross_qty_sold"] - sales["returned_qty"]

    aggregations = {
        # Retain the signed source total for an exact reconciliation audit.
        "raw_qty_sold": ("Qty Sold", "sum"),
        "gross_qty_sold": ("gross_qty_sold", "sum"),
        "returned_qty": ("returned_qty", "sum"),
        "net_qty_sold": ("net_qty_sold", "sum"),
        "transaction_count": ("Qty Sold", "count"),
    }
    if "Sales Amount" in sales.columns:
        aggregations["gross_sales_amount"] = ("Sales Amount", "sum")
    if "Cogs" in sales.columns:
        aggregations["total_cogs"] = ("Cogs", "sum")
    if "Number of Transactions" in sales.columns:
        aggregations["transaction_count"] = ("Number of Transactions", "sum")

    aggregated = (
        sales.groupby(["Product No", "Store", "date"], as_index=False)
        .agg(**aggregations)
    )
    for column in ("gross_qty_sold", "returned_qty", "net_qty_sold"):
        aggregated[column] = aggregated[column].astype("float64")
    return aggregated
