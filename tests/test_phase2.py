"""Synthetic checks for sequential estimated-demand reconstruction."""

import pandas as pd

from src.demand.asof import estimate_demand_asof


def _hierarchy():
    return pd.DataFrame({"Product No": ["p"], "Product Division": ["d"], "Product Subcategory": ["c"]})


def _rows(zero_days=1):
    dates = pd.date_range("2025-06-01", periods=7 + zero_days)
    return pd.DataFrame({"Product No": ["p"] * len(dates), "Store": ["s"] * len(dates), "date": dates, "qty_onhand": [5] * 7 + [0] * zero_days, "stock_known": [True] * len(dates), "gross_qty_sold": [2] * 7 + [1] * zero_days, "returned_qty": [0] * len(dates), "source": ["snapshot_observed"] * len(dates)})


def test_empty_shelf_uses_prior_rate_and_retains_recorded_purchase():
    last = estimate_demand_asof(_rows(), _hierarchy()).iloc[-1]
    assert last.estimated_demand == 2 and last.estimate_fallback == "sku_store_prior_mean" and last.gross_qty_sold == 1


def test_future_sales_do_not_change_an_earlier_estimate():
    original = _rows()
    changed = pd.concat([original, pd.DataFrame({"Product No": ["p"], "Store": ["s"], "date": [pd.Timestamp("2025-06-10")], "qty_onhand": [5], "stock_known": [True], "gross_qty_sold": [100], "returned_qty": [0], "source": ["snapshot_observed"]})], ignore_index=True)
    a = estimate_demand_asof(original, _hierarchy())
    b = estimate_demand_asof(changed, _hierarchy())
    assert a.iloc[-1].estimated_demand == b[b.date == a.iloc[-1].date].iloc[0].estimated_demand


def test_unknown_stock_is_not_treated_as_zero_stock():
    rows = _rows().iloc[:1].copy()
    rows["qty_onhand"] = pd.NA
    rows["stock_known"] = False
    rows["source"] = "unknown_before_anchor"
    row = estimate_demand_asof(rows, _hierarchy()).iloc[0]
    assert row.availability_assessment == "unknown_stock" and row.estimate_fallback == "insufficient_stock_evidence"


def test_same_day_donor_cannot_change_another_pair_estimate():
    dates = pd.date_range("2025-06-01", periods=8)
    rows = pd.DataFrame({"Product No": ["p1"] * 8 + ["p2"] * 8,
        "Store": ["s"] * 16, "date": list(dates) * 2,
        "qty_onhand": [0] * 7 + [5] + [0] * 8,
        "stock_known": [True] * 16, "gross_qty_sold": [0] * 7 + [10] + [1] * 8,
        "returned_qty": [0] * 16, "source": ["snapshot_observed"] * 16})
    hierarchy = pd.DataFrame({"Product No": ["p1", "p2"], "Product Division": ["d", "d"], "Product Subcategory": ["c", "c"]})
    result = estimate_demand_asof(rows, hierarchy)
    p2 = result[result["Product No"] == "p2"].iloc[-1]
    assert p2.estimate_fallback == "insufficient_prior_rate"


def test_shortfall_and_reconciliation_days_are_not_donor_exposure():
    dates = pd.date_range("2025-06-01", periods=8)
    rows = pd.DataFrame({
        "Product No": ["p"] * 8,
        "Store": ["s"] * 8,
        "date": dates,
        "qty_onhand": [1] * 7 + [0],
        "raw_qty_onhand": [1] * 8,
        "stock_known": [True] * 8,
        "gross_qty_sold": [2] * 7 + [0],
        "returned_qty": [1] * 7 + [0],
        "source": ["bridged_assumed"] * 8,
        "unexplained_shortfall": [1] * 7 + [0],
        "reconciliation_adjustment": [0.0] * 8,
    })
    result = estimate_demand_asof(rows, _hierarchy())
    last = result.iloc[-1]
    assert last.availability_assessment == "empty_or_depleted"
    assert last.estimate_fallback == "insufficient_prior_rate"


def test_positive_stock_with_reconciliation_jump_is_not_donor():
    rows = _rows().assign(raw_qty_onhand=5.0, reconciliation_adjustment=0.0, unexplained_shortfall=0.0)
    rows.loc[6, "reconciliation_adjustment"] = 4.0
    rows.loc[7, "qty_onhand"] = 0
    result = estimate_demand_asof(rows, _hierarchy())
    assert result.iloc[6].availability_assessment == "partial_or_discrepant"
    assert result.iloc[7].estimate_fallback == "insufficient_prior_rate"
