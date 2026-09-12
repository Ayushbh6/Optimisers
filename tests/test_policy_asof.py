import numpy as np
import pandas as pd

from src.policy.asof import build_asof_policy_snapshot
from src.policy.engine import compute_inventory_policy, compute_policy_vectors


def test_asof_policy_never_invents_missing_cost():
    forecast = pd.DataFrame({
        "Product No": ["A", "B"], "Store": ["S", "S"],
        "daily_expected_demand": [0.1, 0.1], "demand_std": [1.0, 1.0],
        "information_cutoff": [pd.Timestamp("2026-01-15")] * 2,
    })
    costs = pd.DataFrame({"Product No": ["A"], "Store": ["S"], "unit_cost_as_of": [10.0]})
    policy = build_asof_policy_snapshot(forecast, costs)
    assert policy.loc[policy["Product No"] == "A", "policy_status"].item() == "available"
    missing = policy.loc[policy["Product No"] == "B"].iloc[0]
    assert missing["policy_status"] == "unavailable_missing_cost"
    assert pd.isna(missing["order_up_to_S"])


def test_low_pair_cost_is_preserved_without_euro_one_floor():
    forecast = pd.DataFrame({
        "Product No": ["A"], "Store": ["S"], "daily_expected_demand": [1.0],
        "demand_std": [0.0], "information_cutoff": [pd.Timestamp("2026-01-15")],
    })
    policy = build_asof_policy_snapshot(
        forecast,
        pd.DataFrame({"Product No": ["A"], "Store": ["S"], "unit_cost_as_of": [0.25]}),
    )
    assert policy["unit_cost_as_of"].item() == 0.25
    direct = compute_policy_vectors(
        np.array([1.0]), np.array([0.0]), np.array([0.25]),
        10, 0.95, 0.20, 2.0, 5, 0.004,
    )
    assert direct["order_qty_q"].item() >= 5


def test_standalone_policy_uses_latest_pair_cost_and_marks_missing_pair():
    forecast = pd.DataFrame({
        "Product No": ["A", "B"], "Store": ["S", "S"],
        "daily_expected_demand": [1.0, 1.0], "demand_std": [0.0, 0.0],
    })
    onhand = pd.DataFrame({
        "Product No": ["A", "A"], "Store": ["S", "S"],
        "date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
        "unit_cost": [0.50, 0.25],
    })
    policy = compute_inventory_policy(forecast, onhand).set_index("Product No")
    assert policy.loc["A", "unit_cost"] == 0.25
    assert policy.loc["B", "policy_status"] == "unavailable_missing_cost"
    assert policy.loc["B", "is_stocked"] is False or not bool(policy.loc["B", "is_stocked"])


def test_asof_policy_resolves_dated_cost_at_each_cutoff():
    forecast = pd.DataFrame({
        "Product No": ["A", "A"], "Store": ["S", "S"],
        "daily_expected_demand": [1.0, 1.0], "demand_std": [0.0, 0.0],
        "information_cutoff": [pd.Timestamp("2025-01-15"), pd.Timestamp("2025-03-15")],
    })
    dated_costs = pd.DataFrame({
        "Product No": ["A", "A"], "Store": ["S", "S"],
        "date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
        "unit_cost_as_of": [0.25, 0.75],
    })
    policy = build_asof_policy_snapshot(forecast, dated_costs)
    assert list(policy["unit_cost_as_of"]) == [0.25, 0.75]
