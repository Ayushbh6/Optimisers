"""Command-line pipeline runner for Phase 3: Demand Forecasting.

Usage:
    python -m src.forecast.build_forecast
"""

import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

from src.demand.unconstraining import extract_product_hierarchy
from src.forecast.config import ForecastConfig, DEFAULT_FORECAST_CONFIG
from src.forecast.aggregation import prepare_weekly_demand_series
from src.forecast.disaggregation import compute_sku_demand_shares, disaggregate_forecast
from src.forecast.evaluator import evaluate_holdout_performance
from src.forecast.models import fit_predict_demand
from src.forecast.validator import (
    validate_no_leakage,
    validate_disaggregation,
    validate_mase_baseline,
    validate_non_negativity,
    validate_prediction_intervals,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("build_forecast")


def run_phase3_pipeline(config: ForecastConfig = DEFAULT_FORECAST_CONFIG) -> Path:
    """Execute end-to-end Phase 3 demand forecasting pipeline.

    Args:
        config: Forecasting configuration object.

    Returns:
        Path to the saved artifacts/forecast.parquet file.

    Raises:
        RuntimeError: If any Phase 3 validation checks fail.
        FileNotFoundError: If input demand.parquet is missing.
    """
    start_time = time.time()
    logger.info("=== Starting Phase 3 Pipeline: Hierarchical Intermittent Forecasting ===")

    # 1. Verify input existence
    if not config.demand_parquet_path.exists():
        raise FileNotFoundError(
            f"Phase 2 artifact missing at {config.demand_parquet_path}. "
            f"Please run `python -m src.demand.build_demand` first."
        )

    # 2. Ingest inputs
    logger.info("Loading demand matrix from %s", config.demand_parquet_path)
    demand_df = pd.read_parquet(
        config.demand_parquet_path,
        columns=["Product No", "Store", "date", "unconstrained_demand"],
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

    # 3. Weekly aggregation
    weekly_agg_df, weekly_sku_df = prepare_weekly_demand_series(demand_df, hierarchy_df, config)

    # 4. Temporal Hold-Out Evaluation (Scholar Footwear benchmark)
    eval_metrics = evaluate_holdout_performance(
        weekly_aggregate_df=weekly_agg_df,
        target_division="Scholar Footwear",
        method="croston",
        config=config,
    )

    # 5. Fit model across all aggregate (Subcategory x Store) series
    logger.info("Fitting intermittent forecast models across all aggregate groups...")
    weeks = sorted(weekly_agg_df["week"].unique())
    n_train = int(len(weeks) * config.train_ratio)
    train_weeks = set(weeks[:n_train])
    test_weeks = set(weeks[n_train:])

    agg_groups = weekly_agg_df.groupby(["Product Subcategory", "Store"])
    agg_records = []

    for (subcat, store), group in agg_groups:
        ts_dict = dict(zip(group["week"], group["weekly_demand"]))
        full_ts = np.array([ts_dict.get(w, 0.0) for w in weeks], dtype=np.float64)

        # Fit model on full historical series for forward deployment
        res = fit_predict_demand(full_ts, method="croston", alpha=config.alpha)
        agg_records.append(
            {
                "Product Subcategory": subcat,
                "Store": store,
                "aggregate_expected_demand": res["expected_demand"],
                "aggregate_demand_std": res["demand_std"],
                "method": res["method"],
            }
        )

    agg_forecast_df = pd.DataFrame(agg_records)
    logger.info("Fitted %d aggregate subcategory-store models.", len(agg_forecast_df))

    # 6. Disaggregation down to SKU level
    sku_shares_df = compute_sku_demand_shares(weekly_sku_df, laplace_prior=config.laplace_prior)
    sku_forecast_df = disaggregate_forecast(agg_forecast_df, sku_shares_df, config)

    # 7. Validate all Phase 3 invariants
    v_leakage, msg_leakage, _ = validate_no_leakage(train_weeks, test_weeks)
    v_disagg, msg_disagg, _ = validate_disaggregation(sku_forecast_df, agg_forecast_df, hierarchy_df)
    v_mase, msg_mase, _ = validate_mase_baseline(eval_metrics)
    v_nonneg, msg_nonneg, _ = validate_non_negativity(sku_forecast_df)
    v_intervals, msg_intervals, _ = validate_prediction_intervals(sku_forecast_df)

    logger.info("[✓] NO_LEAKAGE: %s", msg_leakage)
    logger.info("[✓] DISAGGREGATION: %s", msg_disagg)
    logger.info("[✓] BASELINE_MASE: %s", msg_mase)
    logger.info("[✓] NON_NEGATIVE: %s", msg_nonneg)
    logger.info("[✓] PREDICTION_INTERVALS: %s", msg_intervals)

    if not (v_leakage and v_disagg and v_mase and v_nonneg and v_intervals):
        raise RuntimeError("Phase 3 pipeline aborted: Validation checks failed.")

    # 8. Save artifact
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Writing verified artifact to %s ...", config.forecast_parquet_path)
    sku_forecast_df.to_parquet(config.forecast_parquet_path, index=False, engine="pyarrow")

    elapsed = time.time() - start_time
    file_size_mb = config.forecast_parquet_path.stat().st_size / (1024 * 1024)
    logger.info("=== Phase 3 Pipeline Completed Successfully in %.2fs ===", elapsed)
    logger.info("Artifact path: %s (%.2f MB)", config.forecast_parquet_path, file_size_mb)
    logger.info("Total SKU-Store Forecasts: %d", len(sku_forecast_df))
    logger.info("Weekly Expected Demand Sum: %.1f", sku_forecast_df["weekly_expected_demand"].sum())
    logger.info("Daily Expected Demand Sum: %.1f", sku_forecast_df["daily_expected_demand"].sum())

    return config.forecast_parquet_path


if __name__ == "__main__":
    try:
        run_phase3_pipeline()
    except Exception as exc:
        logger.critical("Fatal error during Phase 3 pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
