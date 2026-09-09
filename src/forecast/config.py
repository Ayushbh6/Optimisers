"""Configuration parameters, file paths, and constants for Phase 3 demand forecasting."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ForecastConfig:
    """Immutable configuration container for demand forecasting pipeline."""

    # Project root directory
    project_root: Path = Path(__file__).resolve().parent.parent.parent

    # Input paths
    artifacts_dir: Path = project_root / "artifacts"
    demand_parquet_path: Path = artifacts_dir / "demand.parquet"
    raw_dir: Path = project_root / "data" / "raw"
    inventory_csv_path: Path = raw_dir / "retail_inventory_ml_apl.csv"

    # Artifact output path
    forecast_parquet_path: Path = artifacts_dir / "forecast.parquet"

    # Hierarchy and temporal aggregation
    aggregate_level: str = "Subcategory"  # (Product Subcategory x Store x week)
    time_frequency: str = "W-MON"         # Weekly frequency aligned on Monday

    # Evaluation / Train-Test Split (Anti-leakage)
    train_ratio: float = 0.70             # First ~70% weeks for training
    holdout_ratio: float = 0.30           # Final ~30% weeks for held-out evaluation

    # Model parameters
    alpha: float = 0.1                    # Smoothing factor for non-zero demand size
    beta: float = 0.1                     # Smoothing factor for non-zero demand probability
    laplace_prior: float = 1e-4           # Smoothing constant for SKU disaggregation shares
    forecast_horizon_weeks: int = 4       # Number of future weeks to project

    # Output schema definition
    forecast_columns: tuple = (
        "Product No",
        "Store",
        "forecast_horizon_weeks",
        "weekly_expected_demand",
        "daily_expected_demand",
        "demand_std",
        "lower_bound_95",
        "upper_bound_95",
        "method",
        "aggregate_level",
    )


DEFAULT_FORECAST_CONFIG = ForecastConfig()
