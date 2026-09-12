"""Shared daily forecast snapshots and fair historical benchmarks."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.data.metadata import resolve_metadata
from src.forecast.state import ForecastState


def hierarchy_asof(hierarchy: pd.DataFrame, cutoff: str | pd.Timestamp) -> pd.DataFrame:
    """Return only product facts observed at or before the decision cutoff."""
    return resolve_metadata(hierarchy, cutoff)


def _complete_weeks(history, cutoff):
    """Exclude incomplete leading and trailing weeks for each pair."""
    data = history.copy()
    data['week_start'] = data['date'] - pd.to_timedelta(data['date'].dt.weekday, unit='D')
    keys = ['Product No', 'Store', 'week_start']
    count = data.groupby(keys)['date'].transform('nunique')
    return data[(count == 7) & (data.week_start + pd.Timedelta(days=6) <= cutoff)]


def build_asof_forecast_snapshot(history: pd.DataFrame, hierarchy: pd.DataFrame, cutoff: str | pd.Timestamp, *, demand_column: str = 'estimated_demand', method: str = 'croston', alpha: float = .1, beta: float = .1, laplace_prior: float = 1e-4, history_granularity: str = 'daily') -> pd.DataFrame:
    """Build from dated daily records; completed weekly fixtures remain supported."""
    data = history[pd.to_datetime(history['date']) <= pd.Timestamp(cutoff)].copy()
    if history_granularity == 'weekly':
        data = data[pd.to_datetime(data['week_start']) + pd.Timedelta(days=6) <= pd.Timestamp(cutoff)]
        data = pd.concat([data.assign(date=pd.to_datetime(data.week_start) + pd.Timedelta(days=i), **{demand_column: data[demand_column] / 7}) for i in range(7)], ignore_index=True)
    elif history_granularity != 'daily':
        raise ValueError('Unsupported history granularity')
    pairs = pd.MultiIndex.from_frame(data[['Product No', 'Store']]).unique()
    state = ForecastState(pairs, method=method, alpha=alpha, beta=beta, prior=laplace_prior)
    for day, rows in data.groupby('date', sort=True):
        values = np.zeros(len(pairs)); present = np.zeros(len(pairs), bool)
        rows = rows.groupby(['Product No', 'Store'])[demand_column].sum()
        idx = pairs.get_indexer(rows.index)
        values[idx] = rows.to_numpy(); present[idx] = True
        state.add(day, values, present)
    result = state.snapshot(hierarchy, cutoff)
    result['demand_input'] = demand_column
    return result


def evaluate_forecast_benchmarks(history: pd.DataFrame, hierarchy: pd.DataFrame, evaluation_dates: pd.DatetimeIndex | list, *, observed_column: str = 'gross_purchase_units', estimated_column: str = 'estimated_demand', method: str = 'croston', alpha: float = .1, beta: float = .1, laplace_prior: float = 1e-4) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score all methods on identical dated targets; never fill missing scores."""
    pairs = pd.MultiIndex.from_frame(history[['Product No', 'Store']]).unique()
    estimated = ForecastState(pairs, method=method, alpha=alpha, beta=beta, prior=laplace_prior)
    observed = ForecastState(pairs, method=method, alpha=alpha, beta=beta, prior=laplace_prior)
    evaluation_dates = set(pd.to_datetime(evaluation_dates))
    details = []
    for day, rows in history.groupby('date', sort=True):
        day = pd.Timestamp(day)
        idx = pairs.get_indexer(pd.MultiIndex.from_frame(rows[['Product No', 'Store']]))
        values = np.zeros(len(pairs)); gross = values.copy(); present = np.zeros(len(pairs), bool)
        values[idx] = rows[estimated_column]; gross[idx] = rows[observed_column]; present[idx] = True
        if day in evaluation_dates:
            snapshot = estimated.snapshot(hierarchy, day - pd.Timedelta(days=1))
            snapshot_idx = pairs.get_indexer(pd.MultiIndex.from_frame(snapshot[['Product No', 'Store']]))
            snapshot = snapshot[present[snapshot_idx]].copy(); snapshot_idx = snapshot_idx[present[snapshot_idx]]
            if not snapshot.empty:
                snapshot['target_date'] = day
                for label, state, actual in [('observed', observed, gross), ('estimated', estimated, values)]:
                    complete = [w for w in sorted(state.weeks) if w + pd.Timedelta(days=6) < day]
                    last = complete[-1] if complete else None
                    last_values = np.full(len(pairs), np.nan)
                    total = np.zeros(len(pairs)); count = np.zeros(len(pairs))
                    for week in complete:
                        valid = state.counts[week] == 7
                        total += np.where(valid, state.weeks[week], 0); count += valid
                    if last is not None:
                        valid = state.counts[last] == 7; last_values[valid] = state.weeks[last][valid] / 7
                    average = np.divide(total, count * 7, out=np.full(len(pairs), np.nan), where=count > 0)
                    snapshot[label + '_target_units'] = actual[snapshot_idx]
                    snapshot[label + '_error'] = np.abs(actual[snapshot_idx] - snapshot.daily_expected_demand)
                    snapshot['last_week_' + label + '_error'] = np.abs(actual[snapshot_idx] - last_values[snapshot_idx])
                    snapshot['average_' + label + '_error'] = np.abs(actual[snapshot_idx] - average[snapshot_idx])
                    snapshot[label + '_interval_covered'] = (actual[snapshot_idx] >= snapshot.daily_lower_bound) & (actual[snapshot_idx] <= snapshot.daily_upper_bound)
                details.append(snapshot)
        estimated.add(day, values, present); observed.add(day, gross, present)
    if not details:
        return pd.DataFrame(), pd.DataFrame()
    detail = pd.concat(details, ignore_index=True)
    summary = []
    for label, target in [('observed', 'observed_purchases'), ('estimated', 'estimated_demand')]:
        columns = [label + '_error', 'last_week_' + label + '_error', 'average_' + label + '_error']
        matched = detail.dropna(subset=columns)
        summary.append({'target': target, 'rows': len(matched), 'model_mae': matched[columns[0]].mean(), 'last_completed_week_mae': matched[columns[1]].mean(), 'historical_average_mae': matched[columns[2]].mean(), 'approximate_interval_coverage': matched[label + '_interval_covered'].mean(), 'uncertainty_label': 'normal approximation; not calibrated'})
    return detail, pd.DataFrame(summary)
