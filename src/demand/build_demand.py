"""Command-line pipeline runner to estimate unconstrained demand (Phase 2).

Loads daily on-hand inventory, aggregates daily sales, identifies stockout censoring,
estimates unconstrained demand via hierarchical fallback, validates all invariants,
and saves artifacts/demand.parquet.

Usage:
    python -m src.demand.build_demand
"""

import logging
import sys
import time
from pathlib import Path
import pandas as pd

from src.demand.config import DemandConfig, DEFAULT_DEMAND_CONFIG
from src.demand.censoring import aggregate_daily_sales, align_sales_and_inventory
from src.demand.unconstraining import extract_product_hierarchy, estimate_unconstrained_demand
from src.demand.validator import validate_phase2_all

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("build_demand")


def run_phase2_pipeline(config: DemandConfig = DEFAULT_DEMAND_CONFIG) -> Path:
    """Execute end-to-end Phase 2 unconstrained demand pipeline.

    Args:
        config: Demand configuration object.

    Returns:
        Path to the written artifacts/demand.parquet file.

    Raises:
        RuntimeError: If any Phase 2 validation checks fail.
        FileNotFoundError: If input daily_onhand.parquet or raw CSVs are missing.
    """
    start_time = time.time()
    logger.info("=== Starting Phase 2 Pipeline: Estimate True (Unconstrained) Demand ===")

    # 1. Check prerequisites
    if not config.daily_onhand_parquet_path.exists():
        raise FileNotFoundError(
            f"Phase 1 artifact missing at {config.daily_onhand_parquet_path}. "
            f"Please run `python -m src.data.build_daily_onhand` first."
        )

    # 2. Ingest inputs
    logger.info("Loading daily on-hand inventory from %s", config.daily_onhand_parquet_path)
    onhand_df = pd.read_parquet(
        config.daily_onhand_parquet_path,
        columns=["Product No", "Store", "date", "qty_onhand"],
    )

    logger.info("Loading raw sales transactions from %s", config.sales_csv_path)
    sales_df = pd.read_csv(
        config.sales_csv_path,
        usecols=["Transaction Date", "Product No", "Store", "Qty Sold"],
    )

    logger.info("Loading product hierarchy from %s", config.inventory_csv_path)
    inv_df = pd.read_csv(
        config.inventory_csv_path,
        usecols=[
            "Product No",
            "Product Division",
            "Product Category",
            "Product Subcategory",
            "Product Segment",
        ],
    )
    hierarchy_df = extract_product_hierarchy(inv_df)

    # 3. Aggregate daily sales and align to on-hand grid
    daily_sales_df = aggregate_daily_sales(sales_df)
    aligned_df = align_sales_and_inventory(onhand_df, daily_sales_df)

    # 4. Estimate unconstrained demand
    demand_df = estimate_unconstrained_demand(
        aligned_df=aligned_df,
        hierarchy_df=hierarchy_df,
        config=config,
    )

    # 5. Execute full validation suite
    validation_results = validate_phase2_all(demand_df, onhand_df)
    all_passed = True
    for check_name, (passed, msg, metrics) in validation_results.items():
        prefix = "[✓]" if passed else "[✗]"
        logger.info("%s %s: %s", prefix, check_name.upper(), msg)
        if not passed:
            all_passed = False

    if not all_passed:
        raise RuntimeError("Phase 2 pipeline aborted: Validation checks failed.")

    # 6. Save verified artifact
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing verified artifact to %s ...", config.demand_parquet_path)
    demand_df.to_parquet(config.demand_parquet_path, index=False, engine="pyarrow")

    elapsed = time.time() - start_time
    file_size_mb = config.demand_parquet_path.stat().st_size / (1024 * 1024)
    logger.info("=== Phase 2 Pipeline Completed Successfully in %.2fs ===", elapsed)
    logger.info("Artifact path: %s (%.2f MB)", config.demand_parquet_path, file_size_mb)
    logger.info("Total Rows: %d", len(demand_df))
    logger.info("Observed Demand: %.1f", demand_df["observed_demand"].sum())
    logger.info("Unconstrained Demand: %.1f", demand_df["unconstrained_demand"].sum())

    return config.demand_parquet_path


if __name__ == "__main__":
    try:
        run_phase2_pipeline()
    except Exception as exc:
        logger.critical("Fatal error during Phase 2 pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
