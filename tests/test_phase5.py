"""Synthetic correctness tests for recorded-purchase replay."""

import pandas as pd
import pytest

from src.simulation.replay import DailyReplayInput, ForecastSnapshot, run_causal_replay


def test_replay_enforces_order_delay_and_whole_unit_moq():
    pair = ("p", "s")
    days = [DailyReplayInput(pd.Timestamp(f"2025-01-0{d}"), {pair: 1}) for d in (1, 2, 3)]
    result = run_causal_replay({pair: 0}, days, {pd.Timestamp("2025-01-01"): {pair: 10.0}}, policy_provider=lambda context: {pair: 5} if context.as_of == pd.Timestamp("2025-01-01").date() else {}, lead_time_days=2, minimum_order_qty=5)
    rows = result.ledger.sort_values("date")
    assert rows["arrivals_units"].tolist() == [0, 0, 5] and rows["order_qty_units"].tolist() == [5, 0, 0]
    with pytest.raises(ValueError, match="whole"):
        run_causal_replay({pair: 0}, [DailyReplayInput(pd.Timestamp("2025-01-01"), {})], policy_provider=lambda _: {pair: 0.5})


def test_unfulfilled_targets_do_not_enter_forecast_history():
    pair = ("p", "s")
    seen = []
    def forecast(context):
        seen.append(context.history.fulfilled_purchases[pair])
        return {pair: ForecastSnapshot(0)}
    run_causal_replay({pair: 0}, [DailyReplayInput(pd.Timestamp("2025-01-01"), {pair: 3}), DailyReplayInput(pd.Timestamp("2025-01-02"), {})], forecast_snapshot_provider=forecast)
    assert seen == [(0,), (0, 0)]
    assert all(3 not in values for values in seen)


def test_replay_stock_conservation_and_day_end_returns():
    pair = ("p", "s")
    row = run_causal_replay({pair: 2}, [DailyReplayInput(pd.Timestamp("2025-01-01"), {pair: 2}, {pair: 1})]).ledger.iloc[0]
    assert row.opening_on_hand_units + row.arrivals_units - row.fulfilled_purchases_units + row.returns_units == row.closing_on_hand_units
    assert row.closing_on_hand_units == 1


def test_unknown_initial_stock_is_retained_but_excluded_and_no_po_means_no_tco():
    pair = ("p", "s")
    result = run_causal_replay({pair: None}, [DailyReplayInput(pd.Timestamp("2025-01-01"), {pair: 2})])
    row = result.ledger.iloc[0]
    assert not bool(row.eligible) and row.exclusion_reason == "unknown_initial_stock"
    assert result.metrics.observed_purchase_coverage is None and result.metrics.total_cost_of_ownership_eur is None
