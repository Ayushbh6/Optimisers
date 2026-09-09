"""Command-line pipeline runner for Phase 4: Inventory Policy.

Computes (s, S) reorder rules, validates ordering and capital reduction invariants,
and saves artifacts/policy.parquet.

Usage:
    python -m src.policy.build_policy
"""

import logging
import sys
import time
from pathlib import Path
import pandas as pd

from src.policy.config import PolicyConfig, DEFAULT_POLICY_CONFIG
from src.policy.engine import compute_inventory_policy
from src.policy.validator import (
    validate_ordering_invariant,
    validate_assumptions_recorded,
    validate_capital_reduction,
    validate_moq_compliance,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("build_policy")


def run_phase4_pipeline(config: PolicyConfig = DEFAULT_POLICY_CONFIG) -> Path:
    """Execute end-to-end Phase 4 inventory policy pipeline.

    Args:
        config: Policy configuration container.

    Returns:
        Path to the saved artifacts/policy.parquet file.

    Raises:
        RuntimeError: If any Phase 4 validation checks fail.
        FileNotFoundError: If input forecast or on-hand artifacts are missing.
    """
    start_time = time.time()
    logger.info("=== Starting Phase 4 Pipeline: (s, S) Inventory Policy Optimization ===")

    # 1. Verify prerequisites
    if not config.forecast_parquet_path.exists():
        raise FileNotFoundError(
            f"Phase 3 artifact missing at {config.forecast_parquet_path}. "
            f"Please run `python -m src.forecast.build_forecast` first."
        )

    if not config.daily_onhand_parquet_path.exists():
        raise FileNotFoundError(
            f"Phase 1 artifact missing at {config.daily_onhand_parquet_path}. "
            f"Please run `python -m src.data.build_daily_onhand` first."
        )

    # 2. Ingest inputs
    logger.info("Loading forecast data from %s", config.forecast_parquet_path)
    forecast_df = pd.read_parquet(
        config.forecast_parquet_path,
        columns=["Product No", "Store", "daily_expected_demand", "demand_std"],
    )

    logger.info("Loading on-hand data from %s", config.daily_onhand_parquet_path)
    onhand_df = pd.read_parquet(
        config.daily_onhand_parquet_path,
        columns=["Product No", "Store", "qty_onhand", "unit_cost"],
    )

    # 3. Compute policy
    policy_df = compute_inventory_policy(forecast_df, onhand_df, config)

    # 4. Validate invariants
    v_order, msg_order, _ = validate_ordering_invariant(policy_df)
    v_params, msg_params, _ = validate_assumptions_recorded(policy_df, config)
    v_moq, msg_moq, _ = validate_moq_compliance(policy_df, config.min_order_quantity)
    v_cap, msg_cap, _ = validate_capital_reduction(
        policy_df, onhand_df, baseline_capital=config.observed_inventory_baseline_eur
    )

    logger.info("[✓] ORDERING_INVARIANT: %s", msg_order)
    logger.info("[✓] ASSUMPTIONS_RECORDED: %s", msg_params)
    logger.info("[✓] MOQ_COMPLIANCE: %s", msg_moq)
    logger.info("[✓] CAPITAL_REDUCTION: %s", msg_cap)

    if not (v_order and v_params and v_moq and v_cap):
        raise RuntimeError("Phase 4 pipeline aborted: Validation checks failed.")

    # 5. Save artifact
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing verified artifact to %s ...", config.policy_parquet_path)
    policy_df.to_parquet(config.policy_parquet_path, index=False, engine="pyarrow")

    elapsed = time.time() - start_time
    file_size_mb = config.policy_parquet_path.stat().st_size / (1024 * 1024)
    logger.info("=== Phase 4 Pipeline Completed Successfully in %.2fs ===", elapsed)
    logger.info("Artifact path: %s (%.2f MB)", config.policy_parquet_path, file_size_mb)
    logger.info("Total Policy Pairs: %d", len(policy_df))
    logger.info("Mean Reorder Point (s): %.2f", policy_df["reorder_point_s"].mean())
    logger.info("Mean Order-Up-To (S): %.2f", policy_df["order_up_to_S"].mean())

    return config.policy_parquet_path


if __name__ == "__main__":
    try:
        run_phase4_pipeline()
    except Exception as exc:
        logger.critical("Fatal error during Phase 4 pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
