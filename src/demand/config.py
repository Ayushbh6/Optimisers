"""Configuration parameters, file paths, and constants for Phase 2 demand estimation."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DemandConfig:
    """Immutable configuration container for unconstrained demand pipeline."""

    # Project root directory
    project_root: Path = Path(__file__).resolve().parent.parent.parent

    # Input paths
    raw_dir: Path = project_root / "data" / "raw"
    sales_csv_path: Path = raw_dir / "retail_sales_ml_apl.csv"
    inventory_csv_path: Path = raw_dir / "retail_inventory_ml_apl.csv"
    artifacts_dir: Path = project_root / "artifacts"
    daily_onhand_parquet_path: Path = artifacts_dir / "daily_onhand.parquet"

    # Artifact output path
    demand_parquet_path: Path = artifacts_dir / "demand.parquet"

    # Unconstraining hyperparameters
    min_in_stock_days_sku_store: int = 7
    min_in_stock_days_sku_global: int = 7
    min_in_stock_days_subcat_store: int = 7

    # Output schema definition
    demand_columns: tuple = (
        "Product No",
        "Store",
        "date",
        "observed_demand",
        "unconstrained_demand",
        "is_censored",
        "imputation_method",
    )


DEFAULT_DEMAND_CONFIG = DemandConfig()
