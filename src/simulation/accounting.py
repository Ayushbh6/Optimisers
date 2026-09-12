"""Identical dates, pair scope and dated valuation for both comparison sides."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.run_contract import RunConfig


def compare_stock(ledger: pd.DataFrame, daily: pd.DataFrame, config: RunConfig) -> pd.DataFrame:
    """Value reference and replay with the ledger's same known pair cost."""
    reference = daily[['Product No', 'Store', 'date', 'reference_qty_onhand']]
    data = ledger.merge(reference, on=['Product No', 'Store', 'date'], how='left', validate='one_to_one')
    eligible = data.eligible
    data['matched_valuation'] = eligible & data.reference_qty_onhand.notna() & data.unit_cost_eur.notna() & (data.unit_cost_eur > 0)
    data['reference_value_eur'] = (data.reference_qty_onhand * data.unit_cost_eur).where(data.matched_valuation)
    data['simulated_matched_value_eur'] = (data.closing_on_hand_units * data.unit_cost_eur).where(data.matched_valuation)
    startup_end = pd.Timestamp(config.replay_start) + pd.Timedelta(days=config.startup_days)
    rows = []
    for name, mask in [('full_period', pd.Series(True, index=data.index)), ('first_15_days', data.date < startup_end), ('remaining_days', data.date >= startup_end)]:
        scoped = data[mask & eligible]
        days = int(data.loc[mask, 'date'].nunique())
        target = int(scoped.recorded_gross_purchases_units.sum()); fulfilled = int(scoped.fulfilled_purchases_units.sum())
        reference_sum = scoped.reference_value_eur.sum(min_count=1)
        simulated_sum = scoped.simulated_matched_value_eur.sum(min_count=1)
        orders = scoped[scoped.order_qty_units > 0]
        batches = len(orders[['date', 'Store']].drop_duplicates()); lines = len(orders)
        rows.append({'period': name, 'days': days, 'eligible_pair_days': len(scoped), 'reference_stock_pair_days': int(scoped.reference_qty_onhand.notna().sum()),
            'cost_pair_days': int((scoped.unit_cost_eur.notna() & (scoped.unit_cost_eur > 0)).sum()), 'matched_pair_days': int(scoped.matched_valuation.sum()),
            'recorded_purchases': target, 'fulfilled_purchases': fulfilled, 'unfulfilled_units': target - fulfilled,
            'observed_purchase_coverage': fulfilled / target if target else np.nan,
            'reference_capital_eur': reference_sum / days if days else np.nan,
            'simulated_matched_capital_eur': simulated_sum / days if days else np.nan,
            'reference_holding_cost_eur': reference_sum * config.holding_rate / config.annual_days,
            'simulated_matched_holding_cost_eur': simulated_sum * config.holding_rate / config.annual_days,
            'holding_rate': config.holding_rate, 'order_batches': batches, 'order_lines': lines,
            'batch_cost_eur': batches * config.batch_order_cost, 'line_cost_eur': lines * config.line_order_cost,
            'ordering_cost_eur': batches * config.batch_order_cost + lines * config.line_order_cost,
            'historical_ordering_cost_eur': np.nan, 'total_cost_savings_eur': np.nan,
            'valuation_scope': 'matched pair-days only; not full-chain capital'})
    return pd.DataFrame(rows)


def replay_breakdown(ledger: pd.DataFrame) -> pd.DataFrame:
    """Sum flows by dated division/store; sum each pair's final stock once."""
    eligible = ledger[ledger.eligible].copy()
    if 'on_order_units' not in eligible:
        eligible['on_order_units'] = 0
    keys = ['Product Division', 'Store']
    flow = eligible.groupby(keys, dropna=False).agg(recorded_purchases=('recorded_gross_purchases_units', 'sum'), fulfilled_purchases=('fulfilled_purchases_units', 'sum'), unfulfilled_units=('unfulfilled_purchases_units', 'sum'), order_units=('order_qty_units', 'sum'), pair_days=('eligible', 'size')).reset_index()
    last = eligible.sort_values('date').drop_duplicates(['Product No', 'Store'], keep='last')
    endings = last.groupby(keys, dropna=False).agg(ending_stock_units=('closing_on_hand_units', 'sum'), pending_order_units=('on_order_units', 'sum')).reset_index()
    return flow.merge(endings, on=keys, how='outer').fillna({'ending_stock_units': 0, 'pending_order_units': 0})


def pending_orders(ledger: pd.DataFrame) -> pd.DataFrame:
    """Retain every order line due after the observation window."""
    return ledger[(ledger.order_qty_units > 0) & (ledger.order_arrival_date > ledger.date.max())][['Product No', 'Store', 'date', 'order_arrival_date', 'order_qty_units']].copy()
