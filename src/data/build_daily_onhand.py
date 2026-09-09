"""Pipeline runner script to execute Phase 1 reconstruction and save daily_onhand.parquet."""

import logging
import os
import sys
import time
import pandas as pd

from src.data.config import DEFAULT_CONFIG
from src.data.loader import load_inventory_data, load_sales_data
from src.data.reconstruction import reconstruct_daily_onhand
from src.data.validator import validate_phase1_artifact

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("build_daily_onhand")


def run_pipeline() -> None:
    """Execute the end-to-end Phase 1 daily on-hand reconstruction pipeline."""
    t_start = time.time()
    logger.info("=== Starting Phase 1 Pipeline: Reconstruct Daily On-Hand Stock ===")

    # Ensure artifacts directory exists
    os.makedirs(DEFAULT_CONFIG.artifacts_dir, exist_ok=True)

    # 1. Load raw datasets
    inv_df = load_inventory_data(DEFAULT_CONFIG)
    sales_df = load_sales_data(DEFAULT_CONFIG)

    # 2. Reconstruct daily on-hand
    daily_df, summary = reconstruct_daily_onhand(inv_df, sales_df, DEFAULT_CONFIG)

    # 3. Validate against Phase 1 Success Criteria
    validation_report = validate_phase1_artifact(daily_df, sales_df, DEFAULT_CONFIG)

    for check_name, result in validation_report["checks"].items():
        status_icon = "✓" if result["passed"] else "✗"
        logger.info("[%s] %s: %s", status_icon, check_name.upper(), result["message"])

    if not validation_report["all_passed"]:
        logger.error("Phase 1 validation failed! Artifact will not be written.")
        sys.exit(1)

    # 4. Save artifact to Parquet
    out_path = DEFAULT_CONFIG.daily_onhand_parquet_path
    logger.info("Writing verified artifact to %s ...", out_path)
    daily_df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")

    file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
    elapsed = time.time() - t_start

    logger.info("=== Phase 1 Pipeline Completed Successfully in %.2fs ===", elapsed)
    logger.info("Artifact path: %s (%.2f MB)", out_path, file_size_mb)
    logger.info("Total Daily Records: %s", f"{len(daily_df):,}")
    logger.info("Distinct Products: %d, Stores: %d", summary["distinct_products"], summary["distinct_stores"])
    logger.info(
        "Observed Records: %s (%.1f%%) | Reconstructed Records: %s (%.1f%%)",
        f"{summary['observed_rows_count']:,}",
        summary["observed_rows_count"] / len(daily_df) * 100,
        f"{summary['reconstructed_rows_count']:,}",
        summary["reconstructed_rows_count"] / len(daily_df) * 100,
    )
    logger.info(
        "Sales Reconciliation Rate: %.2f%%",
        validation_report["checks"]["sales_reconciliation"]["metrics"]["effective_rate"] * 100,
    )


if __name__ == "__main__":
    run_pipeline()
