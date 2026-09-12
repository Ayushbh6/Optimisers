"""Regression tests for the causal replay contract and its ledger."""

import pandas as pd
import pytest

from src.simulation.replay import DailyReplayInput, ForecastSnapshot, run_causal_replay
from src.run_contract import RunConfig


def test_late_anchor_activates_on_following_day_and_keeps_prior_purchases_excluded():
    pair = ("p", "late")
    days = [
        DailyReplayInput(pd.Timestamp("2025-01-01"), {pair: 3}),
        DailyReplayInput(pd.Timestamp("2025-01-02"), {pair: 2}),
        DailyReplayInput(pd.Timestamp("2025-01-03"), {pair: 2}),
    ]
    seen = []

    def forecast(context):
        seen.append(context.history.fulfilled_purchases[pair])
        return {pair: ForecastSnapshot(0)} if context.as_of >= pd.Timestamp("2025-01-02").date() else {}

    result = run_causal_replay(
        {pair: None}, days, forecast_snapshot_provider=forecast,
        activation_tape={pair: (pd.Timestamp("2025-01-02"), 4)},
    )
    ledger = result.ledger.sort_values("date")
    assert ledger.iloc[0]["eligible"] is False or not bool(ledger.iloc[0]["eligible"])
    assert list(ledger["fulfilled_purchases_units"]) == [0, 2, 2]
    assert list(ledger["closing_on_hand_units"].dropna()) == [2, 0]
    assert result.metrics.total_target_units == 4
    assert seen[0] == (0,)


def test_pending_orders_are_preserved_after_window_and_store_day_batch_is_distinguishable():
    p1, p2 = ("p1", "s"), ("p2", "s")
    days = [DailyReplayInput(pd.Timestamp("2025-01-01"), {p1: 0, p2: 0})]

    def forecast(context):
        return {p1: ForecastSnapshot(1), p2: ForecastSnapshot(1)}

    result = run_causal_replay(
        {p1: 0, p2: 0}, days,
        {pd.Timestamp("2025-01-01"): {p1: 10, p2: 10}},
        forecast_snapshot_provider=forecast,
        policy_provider=lambda context: {p1: 5, p2: 5},
        lead_time_days=10,
        minimum_order_qty=5,
    )
    ledger = result.ledger
    assert ledger["order_qty_units"].sum() == 10
    assert ledger["on_order_units"].sum() == 10
    assert ledger["arrivals_units"].sum() == 0
    # Both lines belong to one store-day batch; the caller can therefore
    # charge one fixed event plus two line items rather than two fixed events.
    assert ledger.loc[ledger["order_qty_units"] > 0, "date"].nunique() == 1


def test_replay_refuses_mixed_or_stale_output_directory(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    (output / "old.parquet").write_text("old", encoding="utf-8")
    with pytest.raises(FileExistsError):
        # The runner checks this before touching the raw files.
        from src.build_part1 import run_part1
        run_part1(RunConfig(project_root=tmp_path, output_dir=output))
