"""Synthetic checks for raw sales and causal stock reconstruction."""

import pandas as pd

from src.data.config import DataConfig
import pytest

from src.data.loader import aggregate_daily_sales
from src.data.reconstruction import reconstruct_daily_onhand


def _inventory(rows):
    base = {"Stock Unit Cost Price": 10.0, "Stock Unit Selling Price": 20.0, "Stock Status": "Full Price"}
    result = pd.DataFrame([{**base, **row} for row in rows])
    result["Start Date"] = pd.to_datetime(result["Start Date"])
    result["End Date_parsed"] = pd.to_datetime(result["End Date"])
    return result


def _config():
    return DataConfig(observation_start_date="2025-06-01", observation_end_date="2025-06-05")


def test_sales_keep_gross_purchases_and_returns_separate():
    sales = pd.DataFrame({"Product No": ["p", "p"], "Store": ["s", "s"], "date": ["2025-06-01", "2025-06-01"], "Qty Sold": [3, -1], "Is Return": [0, 1]})
    row = aggregate_daily_sales(sales).iloc[0]
    assert row.gross_qty_sold == 3 and row.returned_qty == 1 and row.net_qty_sold == 2


def test_snapshot_is_closing_stock_and_returns_are_day_end():
    inventory = _inventory([{"Product No": "p", "Store": "s", "Start Date": "2025-06-01", "End Date": "2025-06-05", "Qty on hand": 1}])
    sales = pd.DataFrame({"Product No": ["p", "p"], "Store": ["s", "s"], "date": ["2025-06-02", "2025-06-02"], "Qty Sold": [2, -1], "Is Return": [0, 1]})
    result = reconstruct_daily_onhand(inventory, sales, _config())[0]
    day = result[result["date"] == pd.Timestamp("2025-06-02")].iloc[0]
    assert day.qty_onhand == 1 and day.unexplained_shortfall == 1
    assert day.gross_qty_sold == 2 and day.returned_qty == 1


def test_snapshot_reconciliation_uses_day_end_return_timing():
    inventory = _inventory([
        {"Product No": "p", "Store": "s", "Start Date": "2025-06-01", "End Date": "2025-06-01", "Qty on hand": 1},
        {"Product No": "p", "Store": "s", "Start Date": "2025-06-02", "End Date": "2025-06-05", "Qty on hand": 1},
    ])
    sales = pd.DataFrame({"Product No": ["p", "p"], "Store": ["s", "s"], "date": ["2025-06-02", "2025-06-02"], "Qty Sold": [2, -1], "Is Return": [0, 1]})
    result = reconstruct_daily_onhand(inventory, sales, _config())[0]
    row = result[result["date"] == pd.Timestamp("2025-06-02")].iloc[0]
    assert row.qty_onhand == 1
    assert row.reconciliation_adjustment == 0


def test_negative_raw_stock_is_preserved_but_physical_stock_is_floored():
    inventory = _inventory([{"Product No": "p", "Store": "s", "Start Date": "2025-06-01", "End Date": "2025-06-05", "Qty on hand": -2}])
    result, stats = reconstruct_daily_onhand(inventory, pd.DataFrame(columns=["Product No", "Store", "date", "Qty Sold"]), _config())
    assert (result.qty_onhand == 0).all() and result.iloc[0].raw_qty_onhand == -2
    assert stats["raw_negative_records"] == 1


def test_future_interval_end_does_not_change_earlier_causal_rows():
    first = _inventory([{"Product No": "p", "Store": "s", "Start Date": "2025-06-01", "End Date": "2025-06-03", "Qty on hand": 4}])
    later = first.copy()
    # Mutate the parsed value actually used by retrospective expansion.  A
    # test that changes only the display string would miss the old leak.
    later["End Date_parsed"] = pd.Timestamp("2025-06-05")
    sales = pd.DataFrame({"Product No": ["p"], "Store": ["s"], "date": ["2025-06-02"], "Qty Sold": [1]})
    a = reconstruct_daily_onhand(first, sales, _config())[0]
    b = reconstruct_daily_onhand(later, sales, _config())[0]
    cols = ["date", "qty_onhand", "source", "unexplained_shortfall"]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))


def test_quantity_and_return_flag_mismatch_is_rejected():
    bad = pd.DataFrame({"Product No": ["p"], "Store": ["s"], "date": ["2025-06-01"], "Qty Sold": [-3], "Is Return": [0]})
    with pytest.raises(ValueError, match="mismatch"):
        aggregate_daily_sales(bad)


def test_invalid_quantity_is_rejected_instead_of_becoming_zero():
    bad = pd.DataFrame({"Product No": ["p"], "Store": ["s"], "date": ["2025-06-01"], "Qty Sold": ["not-a-number"]})
    with pytest.raises(ValueError, match="invalid Qty Sold"):
        aggregate_daily_sales(bad)
