"""Validation module enforcing Phase 1 Success Criteria and data integrity invariants."""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from src.data.config import DEFAULT_CONFIG, DataConfig
from src.data.loader import aggregate_daily_sales

logger = logging.getLogger(__name__)


def validate_coverage(daily_df: pd.DataFrame) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that every (Product No, Store) pair has a contiguous series with no internal gaps.

    For each active pair, the difference between consecutive calendar dates must equal exactly 1 day.

    Args:
        daily_df: Reconstructed daily on-hand DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating time-series contiguity and coverage across active spans...")

    # Sort to ensure strictly monotonic order per pair
    sorted_df = daily_df.sort_values(["Product No", "Store", "date"]).reset_index(drop=True)

    # Shift date within each pair to check day difference
    date_diff = (
        sorted_df.groupby(["Product No", "Store"])["date"]
        .diff()
        .dt.days
    )

    # First row of each group has NaN diff; all internal subsequent rows must have diff == 1
    internal_gaps_mask = (date_diff.notnull()) & (date_diff != 1)
    internal_gaps_count = int(internal_gaps_mask.sum())
    total_pairs = int(daily_df.groupby(["Product No", "Store"]).ngroups)

    passed = (internal_gaps_count == 0)
    msg = (
        f"Coverage check passed: 100% of {total_pairs:,} pairs have contiguous daily series (0 internal gaps)."
        if passed
        else f"Coverage check failed: Found {internal_gaps_count:,} internal gaps across active spans."
    )

    metrics = {
        "total_pairs": total_pairs,
        "internal_gaps_count": internal_gaps_count,
        "is_contiguous": passed,
    }
    return passed, msg, metrics


def validate_no_overlap(daily_df: pd.DataFrame) -> Tuple[bool, str, int]:
    """Validate that no (Product No, Store, date) key has duplicate records.

    Args:
        daily_df: Reconstructed daily on-hand DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, duplicate_count: int).
    """
    logger.info("Validating key uniqueness (zero duplicate records)...")
    duplicate_count = int(daily_df.duplicated(subset=["Product No", "Store", "date"]).sum())
    passed = (duplicate_count == 0)
    msg = (
        f"Overlap check passed: 0 duplicate (Product No, Store, date) records found in {len(daily_df):,} rows."
        if passed
        else f"Overlap check failed: Found {duplicate_count:,} duplicate daily records."
    )
    return passed, msg, duplicate_count


def validate_entity_counts(
    daily_df: pd.DataFrame,
    expected_products: int = 2326,
    expected_stores: int = 40,
) -> Tuple[bool, str, Dict[str, int]]:
    """Validate that distinct product and store counts match the raw enterprise catalog.

    Args:
        daily_df: Reconstructed daily on-hand DataFrame.
        expected_products: Expected SKU count (default 2,326).
        expected_stores: Expected store count (default 40).

    Returns:
        Tuple of (passed: bool, message: str, counts: dict).
    """
    logger.info("Validating entity counts against raw enterprise baseline...")
    n_products = int(daily_df["Product No"].nunique())
    n_stores = int(daily_df["Store"].nunique())

    passed = (n_products == expected_products) and (n_stores == expected_stores)
    msg = (
        f"Entity counts check passed: {n_products:,} products (expected {expected_products:,}) "
        f"and {n_stores} stores (expected {expected_stores})."
        if passed
        else f"Entity counts check failed: Got {n_products} products (expected {expected_products}) "
        f"and {n_stores} stores (expected {expected_stores})."
    )

    counts = {
        "distinct_products": n_products,
        "expected_products": expected_products,
        "distinct_stores": n_stores,
        "expected_stores": expected_stores,
    }
    return passed, msg, counts


def validate_non_negative(daily_df: pd.DataFrame) -> Tuple[bool, str, int]:
    """Validate that on-hand inventory is strictly non-negative (qty_onhand >= 0) everywhere.

    Args:
        daily_df: Reconstructed daily on-hand DataFrame.

    Returns:
        Tuple of (passed: bool, message: str, negative_count: int).
    """
    logger.info("Validating non-negative inventory policy enforcement...")
    negative_mask = daily_df["qty_onhand"] < 0
    negative_count = int(negative_mask.sum())
    passed = (negative_count == 0)
    msg = (
        f"Non-negativity check passed: 0 negative inventory values across all {len(daily_df):,} daily records."
        if passed
        else f"Non-negativity check failed: Found {negative_count:,} negative values in qty_onhand."
    )
    return passed, msg, negative_count


def validate_sales_reconciliation(
    daily_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    threshold_rate: float = 0.90,
    tolerance_days: int = 1,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that >= 90% of net sales volume matches a corresponding inventory step-down.

    Identifies step-downs in on-hand inventory across consecutive days and verifies that
    daily sales volume aligns with inventory depletion within the allowed tolerance window.

    Args:
        daily_df: Reconstructed daily on-hand DataFrame.
        sales_df: Raw sales ledger.
        threshold_rate: Target reconciliation benchmark (default 0.90 / 90%).
        tolerance_days: Allowed timing offset window in days (default 1).

    Returns:
        Tuple of (passed: bool, message: str, reconciliation_metrics: dict).
    """
    logger.info("Validating sales-to-inventory depletion reconciliation rate...")

    # 1. Total enterprise net sales volume (incorporating returns)
    total_sales_volume = float(sales_df["Qty Sold"].sum())
    daily_sales = aggregate_daily_sales(sales_df)
    daily_sales = daily_sales[daily_sales["net_qty_sold"] > 0].copy()

    # 2. Identify inventory step-downs in daily_df
    # An inventory step-down occurs when qty_onhand[t] < qty_onhand[t-1]
    sorted_inv = daily_df.sort_values(["Product No", "Store", "date"]).reset_index(drop=True)
    sorted_inv["prev_qty"] = (
        sorted_inv.groupby(["Product No", "Store"])["qty_onhand"].shift(1)
    )
    sorted_inv["step_down"] = sorted_inv["prev_qty"] - sorted_inv["qty_onhand"]
    depletions = sorted_inv[sorted_inv["step_down"] > 0][["Product No", "Store", "date", "step_down"]].copy()

    # Create step-down lookup set
    step_down_keys = set(zip(depletions["Product No"], depletions["Store"], depletions["date"]))

    # 3. Match net sales against step-downs (exact same day and within tolerance window)
    exact_matched_qty = 0.0
    tol_matched_qty = 0.0
    exact_matched_events = 0
    tol_matched_events = 0

    for _, row in daily_sales.iterrows():
        p, s, d, q = row["Product No"], row["Store"], row["date"], float(row["net_qty_sold"])
        
        # Exact same-day match
        if (p, s, d) in step_down_keys:
            exact_matched_qty += q
            exact_matched_events += 1
            tol_matched_qty += q
            tol_matched_events += 1
        else:
            # Check within tolerance window: [d - tolerance_days, d + tolerance_days]
            window_matched = False
            for dt in range(-tolerance_days, tolerance_days + 1):
                if dt == 0:
                    continue
                offset_date = d + pd.Timedelta(days=dt)
                if (p, s, offset_date) in step_down_keys:
                    window_matched = True
                    break
            if window_matched:
                tol_matched_qty += q
                tol_matched_events += 1

    exact_reconciliation_rate = exact_matched_qty / total_sales_volume if total_sales_volume > 0 else 0.0
    tol_reconciliation_rate = tol_matched_qty / total_sales_volume if total_sales_volume > 0 else 0.0

    passed = (tol_reconciliation_rate >= threshold_rate) or (exact_reconciliation_rate >= threshold_rate)
    effective_rate = max(exact_reconciliation_rate, tol_reconciliation_rate)

    msg = (
        f"Sales reconciliation check passed: {effective_rate:.2%} of net sales volume matched to inventory "
        f"step-down (Threshold: {threshold_rate:.1%}). Exact same-day: {exact_reconciliation_rate:.2%}, "
        f"Window ±{tolerance_days}d: {tol_reconciliation_rate:.2%}."
        if passed
        else f"Sales reconciliation check failed: Effective rate {effective_rate:.2%} < {threshold_rate:.1%}."
    )

    metrics = {
        "total_sales_volume": total_sales_volume,
        "total_sales_events": len(daily_sales),
        "exact_matched_qty": exact_matched_qty,
        "exact_matched_events": exact_matched_events,
        "exact_reconciliation_rate": exact_reconciliation_rate,
        "tolerance_matched_qty": tol_matched_qty,
        "tolerance_matched_events": tol_matched_events,
        "tolerance_reconciliation_rate": tol_reconciliation_rate,
        "effective_rate": effective_rate,
        "threshold_rate": threshold_rate,
        "is_reconciled": passed,
    }
    return passed, msg, metrics


def validate_phase1_artifact(
    daily_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    config: DataConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """Execute all Phase 1 validation checks and return a unified audit report."""
    logger.info("Executing full Phase 1 validation suite...")

    cov_pass, cov_msg, cov_metrics = validate_coverage(daily_df)
    dup_pass, dup_msg, dup_count = validate_no_overlap(daily_df)
    ent_pass, ent_msg, ent_metrics = validate_entity_counts(
        daily_df,
        expected_products=config.expected_unique_products,
        expected_stores=config.expected_unique_stores,
    )
    nonneg_pass, nonneg_msg, nonneg_count = validate_non_negative(daily_df)
    rec_pass, rec_msg, rec_metrics = validate_sales_reconciliation(daily_df, sales_df)

    all_passed = cov_pass and dup_pass and ent_pass and nonneg_pass and rec_pass

    report = {
        "all_passed": all_passed,
        "checks": {
            "coverage": {"passed": cov_pass, "message": cov_msg, "metrics": cov_metrics},
            "no_overlap": {"passed": dup_pass, "message": dup_msg, "duplicate_count": dup_count},
            "entity_counts": {"passed": ent_pass, "message": ent_msg, "metrics": ent_metrics},
            "non_negative": {"passed": nonneg_pass, "message": nonneg_msg, "negative_count": nonneg_count},
            "sales_reconciliation": {"passed": rec_pass, "message": rec_msg, "metrics": rec_metrics},
        },
    }
    return report
