"""Test suite for Phase 1: Daily On-Hand Stock Reconstruction.

Verifies all requirements and invariants mandated by PLAN.md:
- test_phase1_coverage: no internal gaps across active spans.
- test_phase1_no_overlap: strictly zero duplicate daily records.
- test_phase1_entity_counts: matches raw enterprise catalog (2,326 products, 40 stores).
- test_phase1_nonneg: qty_onhand >= 0 everywhere.
- test_phase1_sales_reconciliation: >= 90% net sales volume matches inventory step-down.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data.config import DEFAULT_CONFIG
from src.data.loader import load_inventory_data, load_sales_data
from src.data.reconstruction import expand_inventory_intervals
from src.data.validator import (
    validate_coverage,
    validate_entity_counts,
    validate_no_overlap,
    validate_non_negative,
    validate_sales_reconciliation,
)


@pytest.fixture(scope="module")
def artifact_df():
    """Load the generated daily_onhand.parquet artifact."""
    artifact_path = DEFAULT_CONFIG.daily_onhand_parquet_path
    assert artifact_path.exists(), f"Artifact not found at {artifact_path}. Run build_daily_onhand first."
    return pd.read_parquet(artifact_path)


@pytest.fixture(scope="module")
def raw_sales_df():
    """Load the raw sales transactions."""
    return load_sales_data(DEFAULT_CONFIG)


@pytest.fixture(scope="module")
def raw_inv_df():
    """Load the raw inventory ledger."""
    return load_inventory_data(DEFAULT_CONFIG)


def test_phase1_coverage(artifact_df):
    """Test that every (Product No, Store) pair has a daily series with no internal gaps across its active span."""
    passed, msg, metrics = validate_coverage(artifact_df)
    assert passed, msg
    assert metrics["internal_gaps_count"] == 0
    assert metrics["total_pairs"] == 60968


def test_phase1_no_overlap(artifact_df):
    """Test that for no (Product No, Store, date) is there more than one qty_onhand value."""
    passed, msg, duplicate_count = validate_no_overlap(artifact_df)
    assert passed, msg
    assert duplicate_count == 0


def test_phase1_entity_counts(artifact_df, raw_inv_df):
    """Test that distinct products = 2,326 and stores = 40 (cross-checked against raw)."""
    raw_products = raw_inv_df["Product No"].nunique()
    raw_stores = raw_inv_df["Store"].nunique()

    assert raw_products == 2326, f"Expected 2326 raw products, got {raw_products}"
    assert raw_stores == 40, f"Expected 40 raw stores, got {raw_stores}"

    passed, msg, counts = validate_entity_counts(
        artifact_df,
        expected_products=raw_products,
        expected_stores=raw_stores,
    )
    assert passed, msg
    assert counts["distinct_products"] == 2326
    assert counts["distinct_stores"] == 40


def test_phase1_nonneg(artifact_df):
    """Test that final qty_onhand >= 0 everywhere (negatives resolved per documented policy)."""
    passed, msg, negative_count = validate_non_negative(artifact_df)
    assert passed, msg
    assert negative_count == 0
    assert (artifact_df["qty_onhand"] < 0).sum() == 0


def test_phase1_sales_reconciliation(artifact_df, raw_sales_df):
    """Test that >= 90% of net sales volume can be matched to a same-day inventory step-down (within tolerance)."""
    passed, msg, metrics = validate_sales_reconciliation(
        artifact_df,
        raw_sales_df,
        threshold_rate=0.90,
        tolerance_days=1,
    )
    assert passed, msg
    assert metrics["effective_rate"] >= 0.90, f"Effective reconciliation rate {metrics['effective_rate']:.4f} < 0.90"


def test_phase1_synthetic_expansion_edge_cases():
    """Unit test interval expansion with synthetic edge cases: negatives, overlaps, and sentinel dates."""
    synthetic_inv = pd.DataFrame(
        {
            "Product No": ["TEST_SKU", "TEST_SKU", "TEST_SKU_2"],
            "Store": ["STR_1", "STR_1", "STR_1"],
            "Start Date": pd.to_datetime(["2025-06-01", "2025-06-05", "2025-06-01"]),
            "End Date_parsed": pd.to_datetime(["2025-06-05", "2025-06-08", "2025-06-03"]),
            "Qty on hand": [-2, 5, 0],
            "Stock Unit Cost Price": [10.0, 10.0, 15.0],
            "Stock Unit Selling Price": [20.0, 20.0, 30.0],
            "Stock Status": ["Full Price", "Full Price", "Full Price"],
        }
    )

    expanded, stats = expand_inventory_intervals(synthetic_inv)

    # 1. Check negative flooring
    assert stats["raw_negative_records_floored"] == 1
    assert (expanded["qty_onhand"] < 0).sum() == 0
    assert expanded[expanded["date"] == "2025-06-01"]["qty_onhand"].iloc[0] == 0.0

    # 2. Check overlap conflict resolution on 2025-06-05: later Start Date (2025-06-05 with Qty=5) must win
    overlap_row = expanded[(expanded["Product No"] == "TEST_SKU") & (expanded["date"] == "2025-06-05")]
    assert len(overlap_row) == 1
    assert overlap_row["qty_onhand"].iloc[0] == 5.0
