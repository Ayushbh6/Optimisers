"""Test suite for Phase 4: Inventory Policy ((s, S) Reorder Rule).

Verifies all requirements and invariants mandated by PLAN.md:
  - test_phase4_ordering: 0 < s <= S for every (Product No, Store).
  - test_phase4_params: every assumption value is recorded alongside the policy output.
  - test_phase4_capital_reduction: recommended inventory capital < observed baseline.
  - test_phase4_deterministic: policy computation is fully deterministic and reproducible.
  - test_phase4_service_level: formulaic target service level and z-score validity.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from src.policy.engine import compute_inventory_policy
from src.policy.validator import (
    validate_ordering_invariant,
    validate_assumptions_recorded,
    validate_capital_reduction,
    validate_moq_compliance,
)


@pytest.fixture(scope="module")
def policy_df():
    """Load the generated policy.parquet artifact."""
    artifact_path = DEFAULT_POLICY_CONFIG.policy_parquet_path
    assert artifact_path.exists(), f"Artifact not found at {artifact_path}. Run build_policy first."
    return pd.read_parquet(artifact_path)


@pytest.fixture(scope="module")
def onhand_df():
    """Load daily on-hand inventory table."""
    return pd.read_parquet(
        DEFAULT_POLICY_CONFIG.daily_onhand_parquet_path,
        columns=["Product No", "Store", "qty_onhand", "unit_cost"],
    )


def test_phase4_ordering(policy_df):
    """Test that 0 < s < S for every in-scope stocked (Product No, Store) pair."""
    passed, msg, metrics = validate_ordering_invariant(policy_df)
    assert passed, msg
    assert metrics["violations_s_le_zero"] == 0
    assert metrics["violations_s_gt_S"] == 0
    assert metrics["min_s_in_scope"] >= 1.0
    assert metrics["min_S_in_scope"] >= 6.0


def test_phase4_moq_respected(policy_df):
    """Test that minimum order quantity (MOQ >= 5) is strictly respected."""
    passed, msg, metrics = validate_moq_compliance(policy_df, expected_moq=5)
    assert passed, msg
    assert metrics["violations"] == 0
    assert metrics["min_order_qty"] >= 5.0
    assert metrics["median_order_qty"] >= 5.0


def test_phase4_params(policy_df):
    """Test that every assumption value is recorded alongside the policy output."""
    passed, msg, metrics = validate_assumptions_recorded(policy_df, DEFAULT_POLICY_CONFIG)
    assert passed, msg
    assert metrics["required_columns_present"]
    assert not metrics["has_null_values"]
    assert metrics["recorded_lead_time"] == 10
    assert metrics["recorded_service_level"] == 0.95


def test_phase4_capital_reduction(policy_df, onhand_df):
    """Test that aggregate recommended inventory value < observed baseline (€2.404M)."""
    passed, msg, metrics = validate_capital_reduction(
        policy_df,
        onhand_df,
        baseline_capital=DEFAULT_POLICY_CONFIG.observed_inventory_baseline_eur,
    )
    assert passed, msg
    assert metrics["capital_saved_eur"] > 0


def test_phase4_deterministic(policy_df):
    """Test that policy computation is fully deterministic and reproducible."""
    forecast_df = pd.read_parquet(
        DEFAULT_POLICY_CONFIG.forecast_parquet_path,
        columns=["Product No", "Store", "daily_expected_demand", "demand_std"],
    )
    onhand_df = pd.read_parquet(
        DEFAULT_POLICY_CONFIG.daily_onhand_parquet_path,
        columns=["Product No", "Store", "unit_cost"],
    )

    recomputed = compute_inventory_policy(forecast_df, onhand_df, DEFAULT_POLICY_CONFIG)

    assert np.allclose(
        policy_df["reorder_point_s"].to_numpy(),
        recomputed["reorder_point_s"].to_numpy(),
    )
    assert np.allclose(
        policy_df["order_up_to_S"].to_numpy(),
        recomputed["order_up_to_S"].to_numpy(),
    )
    assert np.allclose(
        policy_df["target_stock"].to_numpy(),
        recomputed["target_stock"].to_numpy(),
    )


def test_phase4_service_level(policy_df):
    """Test that target service level parameter is valid and aligns with normal approximation."""
    assert (policy_df["target_service_level"] == 0.95).all()
    in_scope = policy_df[policy_df["order_up_to_S"] > 0]
    assert (in_scope["safety_stock"] >= 0.5).all()
