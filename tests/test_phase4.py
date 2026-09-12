"""Synthetic checks for dated, pair-local policy calculations."""

import pandas as pd

from src.policy.asof import build_asof_policy_snapshot
from src.policy.config import PolicyConfig


def _forecast():
    return pd.DataFrame({"Product No": ["p", "q"], "Store": ["s", "s"], "daily_expected_demand": [1.0, 1.0], "demand_std": [0.0, 0.0], "information_cutoff": [pd.Timestamp("2025-06-01")] * 2})


def test_missing_cost_makes_policy_unavailable_without_fake_substitution():
    result = build_asof_policy_snapshot(_forecast(), pd.DataFrame({"Product No": ["p"], "Store": ["s"], "unit_cost_as_of": [10.0]}), PolicyConfig())
    missing = result[result["Product No"] == "q"].iloc[0]
    assert missing.policy_status == "unavailable_missing_cost" and pd.isna(missing.order_qty_q) and not bool(missing.is_stocked)


def test_cost_is_pair_local():
    costs = pd.DataFrame({"Product No": ["p", "q"], "Store": ["s", "s"], "unit_cost_as_of": [2.0, 20.0]})
    result = build_asof_policy_snapshot(_forecast(), costs, PolicyConfig()).set_index("Product No")
    assert result.loc["p", "unit_cost_as_of"] == 2.0 and result.loc["q", "unit_cost_as_of"] == 20.0


def test_policy_keeps_explicit_default_moq():
    costs = pd.DataFrame({"Product No": ["p", "q"], "Store": ["s", "s"], "unit_cost_as_of": [10.0, 10.0]})
    result = build_asof_policy_snapshot(_forecast(), costs, PolicyConfig(min_order_quantity=5))
    assert (result["min_order_qty"] == 5).all()
