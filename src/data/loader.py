"""Data ingestion and schema validation module for retail sales and inventory ledgers."""

import logging
from typing import Optional
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

    df["Transaction Date"] = pd.to_datetime(df["Transaction Date"])
    return df


def aggregate_daily_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw sales transactions into net daily sales per (Product No, Store, Date).

    Net quantity accounts for customer returns (where Is Return = 1 and Qty Sold is negative).

    Args:
        sales_df: Raw or filtered sales ledger.

    Returns:
        pd.DataFrame: Aggregated daily net sales per SKU-Store.
    """
    aggregated = (
        sales_df.groupby(["Product No", "Store", "Transaction Date"], as_index=False)
        .agg(
            net_qty_sold=("Qty Sold", "sum"),
            gross_sales_amount=("Sales Amount", "sum"),
            total_cogs=("Cogs", "sum"),
            transaction_count=("Number of Transactions", "sum")
            if "Number of Transactions" in sales_df.columns
            else ("Qty Sold", "count"),
        )
        .rename(columns={"Transaction Date": "date"})
    )
    return aggregated
