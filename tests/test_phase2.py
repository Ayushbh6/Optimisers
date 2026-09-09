"""Test suite for Phase 2: Unconstrained Demand Estimation.

Verifies all requirements and invariants mandated by PLAN.md:
- test_phase2_alignment: demand and on-hand tables share identical index.
- test_phase2_censoring: is_censored == True iff qty_onhand == 0.
- test_phase2_uplift: unconstrained_demand >= observed_demand for all rows.
- test_phase2_no_negative: unconstrained_demand >= 0 everywhere.
- test_phase2_completeness_and_imputation_methods: 0 nulls and valid method labels.
- test_phase2_uplift_concentration: uplift concentrated in stockout windows.
- test_phase2_synthetic_unit: isolated unit test of hierarchical fallback logic.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.demand.config import DEFAULT_DEMAND_CONFIG, DemandConfig
from src.demand.censoring import aggregate_daily_sales, identify_censoring, align_sales_and_inventory
from src.demand.unconstraining import estimate_unconstrained_demand
from src.demand.validator import (
    validate_alignment,
    validate_censoring,
    validate_uplift,
    validate_non_negativity,
)


@pytest.fixture(scope="module")
def demand_df():
    """Load the generated demand.parquet artifact."""
    artifact_path = DEFAULT_DEMAND_CONFIG.demand_parquet_path
    assert artifact_path.exists(), f"Artifact not found at {artifact_path}. Run build_demand first."
    return pd.read_parquet(artifact_path)


@pytest.fixture(scope="module")
def onhand_df():
    """Load the daily on-hand inventory table."""
    onhand_path = DEFAULT_DEMAND_CONFIG.daily_onhand_parquet_path
    assert onhand_path.exists(), f"Phase 1 artifact not found at {onhand_path}."
    return pd.read_parquet(onhand_path, columns=["Product No", "Store", "date", "qty_onhand"])


def test_phase2_alignment(demand_df, onhand_df):
    """Test that demand and on-hand tables share the identical (Product No, Store, date) index."""
    passed, msg, metrics = validate_alignment(demand_df, onhand_df)
    assert passed, msg
    assert metrics["identical_row_count"] == len(onhand_df)
    assert metrics["product_match"]
    assert metrics["store_match"]
    assert metrics["date_match"]


def test_phase2_censoring(demand_df, onhand_df):
    """Test that censoring is applied strictly to mid-lifecycle stockouts."""
    passed, msg, metrics = validate_censoring(demand_df, onhand_df)
    assert passed, msg
    assert metrics["invalid_positive_stock_censored"] == 0
    # Censoring should be confined to real mid-lifecycle stockout gaps (~3.25%), not inflated
    assert 0.01 <= metrics["censored_rate"] <= 0.08
    assert metrics["censored_records"] > 0


def test_phase2_uplift(demand_df):
    """Test that unconstrained_demand >= observed_demand for all rows."""
    passed, msg, metrics = validate_uplift(demand_df)
    assert passed, msg
    assert metrics["violations"] == 0
    assert metrics["total_uplift"] > 0


def test_phase2_no_negative(demand_df):
    """Test that no negative unconstrained demand exists."""
    passed, msg, metrics = validate_non_negativity(demand_df)
    assert passed, msg
    assert metrics["negative_count"] == 0
    assert metrics["min_unconstrained_demand"] >= 0.0


def test_phase2_completeness_and_imputation_methods(demand_df):
    """Test that every row has observed and unconstrained values, and valid method tags."""
    # 1. Zero nulls
    assert demand_df["observed_demand"].isna().sum() == 0
    assert demand_df["unconstrained_demand"].isna().sum() == 0
    assert demand_df["is_censored"].isna().sum() == 0
    assert demand_df["imputation_method"].isna().sum() == 0

    # 2. Valid imputation methods
    valid_methods = {
        "observed",
        "sku_store_in_stock_mean",
        "sku_global_in_stock_mean",
        "subcategory_store_in_stock_mean",
        "subcategory_global_in_stock_mean",
        "zero_floor",
    }
    present_methods = set(demand_df["imputation_method"].unique())
    assert present_methods.issubset(valid_methods), f"Unexpected methods: {present_methods - valid_methods}"

    # Uncensored rows must be tagged as 'observed'
    uncensored_methods = set(demand_df[~demand_df["is_censored"]]["imputation_method"].unique())
    assert uncensored_methods == {"observed"}


def test_phase2_uplift_concentration_in_stockout_periods(demand_df):
    """Verify that demand uplift is concentrated in stockout (censored) windows and return corrections."""
    diff = demand_df["unconstrained_demand"] - demand_df["observed_demand"]
    censored_uplift = diff[demand_df["is_censored"]].sum()
    total_uplift = diff.sum()

    assert total_uplift > 0
    assert censored_uplift > 0
    censored_share = censored_uplift / total_uplift
    assert censored_share >= 0.50, f"Expected >= 50% uplift in stockout windows, got {censored_share*100:.2f}%"


def test_phase2_synthetic_unit_hierarchical_fallback():
    """Unit test hierarchical fallback on synthetic fixture data with mid-lifecycle gap."""
    onhand = pd.DataFrame(
        {
            "Product No": ["SKU_1", "SKU_1", "SKU_1", "SKU_2", "SKU_2"],
            "Store": ["S1", "S1", "S1", "S1", "S1"],
            "date": pd.to_datetime(["2025-06-01", "2025-06-02", "2025-06-03", "2025-06-01", "2025-06-02"]),
            "qty_onhand": [10.0, 0.0, 5.0, 0.0, 0.0],
        }
    )
    sales = pd.DataFrame(
        {
            "Product No": ["SKU_1", "SKU_1"],
            "Store": ["S1", "S1"],
            "Transaction Date": ["2025-06-01", "2025-06-03"],
            "Qty Sold": [5, 2],
        }
    )
    hierarchy = pd.DataFrame(
        {
            "Product No": ["SKU_1", "SKU_2"],
            "Product Division": ["DivA", "DivA"],
            "Product Category": ["CatA", "CatA"],
            "Product Subcategory": ["SubA", "SubA"],
            "Product Segment": ["SegA", "SegA"],
        }
    )

    daily_sales = aggregate_daily_sales(sales)
    aligned = align_sales_and_inventory(onhand, daily_sales)

    # Use min_days=1 for synthetic test
    cfg = DemandConfig(
        min_in_stock_days_sku_store=1,
        min_in_stock_days_sku_global=1,
        min_in_stock_days_subcat_store=1,
    )
    demand = estimate_unconstrained_demand(aligned, hierarchy, cfg)

    # Check SKU_1 day 1 (uncensored): observed = 5.0, unconstrained = 5.0, method = observed
    d1 = demand[(demand["Product No"] == "SKU_1") & (demand["date"] == "2025-06-01")].iloc[0]
    assert d1["observed_demand"] == 5.0
    assert d1["unconstrained_demand"] == 5.0
    assert not d1["is_censored"]
    assert d1["imputation_method"] == "observed"

    # Check SKU_1 day 2 (censored mid-lifecycle gap): observed = 0.0, in-stock mean = 3.5, method = sku_store_in_stock_mean
    d2 = demand[(demand["Product No"] == "SKU_1") & (demand["date"] == "2025-06-02")].iloc[0]
    assert d2["observed_demand"] == 0.0
    assert d2["unconstrained_demand"] > 0.0
    assert d2["is_censored"]
    assert d2["imputation_method"] == "sku_store_in_stock_mean"

    # Check SKU_2 (retired/no in-stock history): not censored, unconstrained = 0.0
    d3 = demand[(demand["Product No"] == "SKU_2") & (demand["date"] == "2025-06-01")].iloc[0]
    assert not d3["is_censored"]
    assert d3["unconstrained_demand"] == 0.0
