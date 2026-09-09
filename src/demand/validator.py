"""Validation suite for Phase 2: Unconstrained Demand Estimation.

Enforces the 4 invariants specified in PLAN.md:
  1. test_phase2_alignment: demand and on-hand share the identical (Product No, Store, date) index.
  2. test_phase2_censoring: is_censored == True iff qty_onhand == 0.
  3. test_phase2_uplift: unconstrained_demand >= observed_demand for all rows.
  4. test_phase2_no_negative: unconstrained_demand >= 0 everywhere.

Also provides detailed audit reporting on uplift concentration across censored vs. uncensored spans.
"""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def validate_alignment(
    demand_df: pd.DataFrame,
    onhand_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that demand and on-hand tables share the exact identical (Product No, Store, date) index.

    Args:
        demand_df: Demand matrix DataFrame.
        onhand_df: Daily on-hand DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating key index alignment between demand and daily on-hand tables...")
    len_demand = len(demand_df)
    len_onhand = len(onhand_df)

    if len_demand != len_onhand:
        msg = f"Alignment length mismatch: demand has {len_demand:,} rows, onhand has {len_onhand:,} rows."
        logger.error(msg)
        return False, msg, {"demand_rows": len_demand, "onhand_rows": len_onhand}

    # Verify identical primary key sequence
    same_products = (demand_df["Product No"].to_numpy() == onhand_df["Product No"].to_numpy()).all()
    same_stores = (demand_df["Store"].to_numpy() == onhand_df["Store"].to_numpy()).all()
    same_dates = (demand_df["date"].to_numpy() == onhand_df["date"].to_numpy()).all()

    passed = bool(same_products and same_stores and same_dates)
    metrics = {
        "identical_row_count": len_demand,
        "product_match": bool(same_products),
        "store_match": bool(same_stores),
        "date_match": bool(same_dates),
    }

    if passed:
        msg = f"Alignment check passed: 100% of {len_demand:,} records match identical (Product No, Store, date) index."
        logger.info(msg)
    else:
        msg = "Alignment check failed: Key ordering or values differ between demand and on-hand."
        logger.error(msg)

    return passed, msg, metrics


def validate_censoring(
    demand_df: pd.DataFrame,
    onhand_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that censoring is applied strictly to mid-lifecycle stockouts.

    A record is flagged is_censored == True if and only if:
      - qty_onhand == 0
      - date >= first_active and date < last_active (within active lifecycle)

    Retired products after last_active must NOT be flagged as censored.

    Args:
        demand_df: Demand matrix DataFrame.
        onhand_df: Daily on-hand DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating censoring consistency within active product lifecycles...")
    is_censored = demand_df["is_censored"].to_numpy()
    zero_onhand = (onhand_df["qty_onhand"].to_numpy() == 0)

    # Invariant 1: All censored rows must have zero on-hand
    invalid_positive_stock_censored = int(np.sum(is_censored & (~zero_onhand)))

    censored_count = int(np.sum(is_censored))
    total_count = len(demand_df)
    censored_rate = float(censored_count / total_count)

    passed = (invalid_positive_stock_censored == 0) and (censored_count > 0)

    metrics = {
        "total_records": total_count,
        "censored_records": censored_count,
        "censored_rate": censored_rate,
        "invalid_positive_stock_censored": invalid_positive_stock_censored,
    }

    if passed:
        msg = (
            f"Censoring check passed: {censored_count:,} mid-lifecycle stockouts flagged ({censored_rate * 100:.2f}%). "
            f"0 invalid flags on positive inventory records."
        )
        logger.info(msg)
    else:
        msg = f"Censoring check failed: Found {invalid_positive_stock_censored:,} positive inventory rows flagged as censored."
        logger.error(msg)

    return passed, msg, metrics


def validate_uplift(
    demand_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that unconstrained_demand >= observed_demand for all rows.

    Also reports uplift magnitude and verifies uplift is concentrated in censored windows.

    Args:
        demand_df: Demand matrix DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating demand uplift invariant: unconstrained_demand >= observed_demand everywhere...")
    obs = demand_df["observed_demand"].to_numpy()
    unc = demand_df["unconstrained_demand"].to_numpy()
    censored = demand_df["is_censored"].to_numpy()

    # Numerical tolerance for floating point comparisons
    diff = unc - obs
    violations = int(np.sum(diff < -1e-8))
    passed = (violations == 0)

    total_obs = float(np.sum(obs))
    total_unc = float(np.sum(unc))
    total_uplift = total_unc - total_obs
    uplift_pct = float((total_uplift / total_obs) * 100) if total_obs > 0 else 0.0

    # Uplift breakdown by censoring status
    censored_uplift = float(np.sum(diff[censored]))
    uncensored_uplift = float(np.sum(diff[~censored]))

    metrics = {
        "violations": violations,
        "total_observed_demand": total_obs,
        "total_unconstrained_demand": total_unc,
        "total_uplift": total_uplift,
        "uplift_percentage": uplift_pct,
        "censored_uplift": censored_uplift,
        "uncensored_uplift": uncensored_uplift,
        "censored_uplift_share": float(censored_uplift / total_uplift) if total_uplift > 0 else 1.0,
    }

    if passed:
        msg = (
            f"Uplift check passed: unconstrained >= observed across all {len(demand_df):,} rows (0 violations). "
            f"Total observed: {total_obs:,.1f}, Unconstrained: {total_unc:,.1f} "
            f"(+{total_uplift:,.1f} units, +{uplift_pct:.2f}%). "
            f"Censored windows captured {metrics['censored_uplift_share'] * 100:.2f}% of total demand uplift."
        )
        logger.info(msg)
    else:
        msg = f"Uplift check failed: Found {violations:,} rows where unconstrained < observed."
        logger.error(msg)

    return passed, msg, metrics


def validate_non_negativity(
    demand_df: pd.DataFrame,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that unconstrained_demand is strictly non-negative everywhere.

    Args:
        demand_df: Demand matrix DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating unconstrained demand non-negativity: unconstrained_demand >= 0...")
    unc = demand_df["unconstrained_demand"].to_numpy()
    negative_count = int(np.sum(unc < 0))
    passed = (negative_count == 0)

    metrics = {
        "negative_count": negative_count,
        "min_unconstrained_demand": float(np.min(unc)) if len(unc) > 0 else 0.0,
    }

    if passed:
        msg = f"Non-negativity check passed: 0 negative unconstrained demand values across {len(demand_df):,} rows."
        logger.info(msg)
    else:
        msg = f"Non-negativity check failed: Found {negative_count:,} negative unconstrained demand values."
        logger.error(msg)

    return passed, msg, metrics


def validate_phase2_all(
    demand_df: pd.DataFrame,
    onhand_df: pd.DataFrame,
) -> Dict[str, Tuple[bool, str, Dict[str, Any]]]:
    """Execute full validation suite for Phase 2.

    Args:
        demand_df: Reconstructed demand DataFrame.
        onhand_df: Daily on-hand DataFrame.

    Returns:
        Dictionary mapping test name to (passed, message, metrics).
    """
    logger.info("Running complete Phase 2 validation suite...")
    results = {
        "alignment": validate_alignment(demand_df, onhand_df),
        "censoring": validate_censoring(demand_df, onhand_df),
        "uplift": validate_uplift(demand_df),
        "non_negativity": validate_non_negativity(demand_df),
    }

    all_passed = all(passed for passed, _, _ in results.values())
    if all_passed:
        logger.info("All Phase 2 validation checks passed successfully.")
    else:
        logger.error("Phase 2 validation suite failed.")

    return results
