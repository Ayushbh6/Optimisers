"""Configuration parameters, file paths, and constants for Phase 1 data pipeline."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataConfig:
    """Immutable configuration container for retail data sources and artifacts."""

    # Project root directory
    project_root: Path = Path(__file__).resolve().parent.parent.parent

    # Raw data paths
    raw_dir: Path = project_root / "data" / "raw"
    sales_csv_path: Path = raw_dir / "retail_sales_ml_apl.csv"
    inventory_csv_path: Path = raw_dir / "retail_inventory_ml_apl.csv"

    # Artifact output paths
    artifacts_dir: Path = project_root / "artifacts"
    daily_onhand_parquet_path: Path = artifacts_dir / "daily_onhand.parquet"

    # Date horizon & sentinel constants
    observation_start_date: str = "2025-06-01"
    observation_end_date: str = "2026-04-24"
    sentinel_end_date: str = "9999-12-31"

    # Expected entity benchmarks from ground-truth audit
    expected_unique_products: int = 2326
    expected_unique_stores: int = 40
    expected_total_calendar_days: int = 328

    # Schema definitions
    inventory_required_columns: tuple = (
        "Start Date",
        "End Date",
        "Stock Status",
        "Product No",
        "Store",
        "Qty on hand",
        "Stock Unit Cost Price",
        "Stock Unit Selling Price",
    )

    sales_required_columns: tuple = (
        "Transaction Date",
        "Product No",
        "Store",
        "Qty Sold",
        "Sales Amount",
        "Cogs",
        "Sales Type",
        "Is Return",
    )

    daily_onhand_columns: tuple = (
        "Product No",
        "Store",
        "date",
        "qty_onhand",
        "raw_qty_onhand",
        "unit_cost",
        "unit_selling_price",
        "stock_status",
        "source",
        "stock_known",
        "reconciliation_adjustment",
        "unexplained_shortfall",
    )


DEFAULT_CONFIG = DataConfig()
