"""Compact daily history with completed-week fits and daily product shares."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.data.metadata import resolve_metadata, category_keys
from src.forecast.models import fit_predict_demand


class ForecastState:
    """Retain weekly totals and daily share totals, without retaining future data."""

    def __init__(self, pairs: pd.MultiIndex | list, *, method: str = 'croston', alpha: float = .1, beta: float = .1, prior: float = 1e-4) -> None:
        self.pairs = list(pairs)
        self.method, self.alpha, self.beta, self.prior = method, alpha, beta, prior
        self.weeks = {}; self.counts = {}; self.totals = np.zeros(len(pairs))
        self.first = None; self.last = None; self.seen = np.zeros(len(pairs), bool)

    def add(self, day: str | pd.Timestamp, values: np.ndarray, present: np.ndarray | None = None) -> None:
        """Add only this day's observable or historically estimated purchases."""
        day = pd.Timestamp(day)
        if self.last is not None and day <= self.last:
            raise ValueError('Forecast history must advance one date at a time')
        values = np.asarray(values, float)
        present = np.ones(len(values), bool) if present is None else np.asarray(present, bool)
        monday = day - pd.Timedelta(days=day.weekday())
        if monday not in self.weeks:
            self.weeks[monday] = np.zeros(len(values)); self.counts[monday] = np.zeros(len(values), np.int16)
        self.weeks[monday] += np.where(present, values, 0)
        self.counts[monday] += present
        self.totals += np.where(present, values, 0)
        self.seen |= present
        self.first = day if self.first is None else self.first
        self.last = day

    def snapshot(self, hierarchy: pd.DataFrame, cutoff: str | pd.Timestamp) -> pd.DataFrame:
        """Fit completed weeks; use all transactions through cutoff for shares."""
        cutoff = pd.Timestamp(cutoff)
        if self.last is not None and self.last > cutoff:
            raise ValueError('Forecast state contains future history')
        metadata = resolve_metadata(hierarchy, cutoff, self.pairs)
        categories = category_keys(metadata)
        keys = [(category, store) if category is not None and seen else None
                for category, (_, store), seen in zip(categories, self.pairs, self.seen)]
        codes, unique = pd.factorize(pd.Series(keys, dtype=object), sort=False)
        valid = codes >= 0
        weeks = [w for w in sorted(self.weeks) if w + pd.Timedelta(days=6) <= cutoff]
        matrix = np.zeros((len(unique), len(weeks)))
        exposed = np.zeros((len(unique), len(weeks)), bool)
        for j, week in enumerate(weeks):
            donors = valid & (self.counts[week] == 7)
            matrix[:, j] = np.bincount(codes[donors], weights=self.weeks[week][donors], minlength=len(unique))
            exposed[:, j] = np.bincount(codes[donors], minlength=len(unique)) > 0
        mu = np.full(len(unique), np.nan); std = mu.copy(); used = np.zeros(len(unique), int)
        for i in range(len(unique)):
            known = np.flatnonzero(exposed[i])
            if len(known):
                # No observations before the group first has a completed week.
                series = matrix[i, known[0]:]
                fit = fit_predict_demand(series, self.method, self.alpha, self.beta)
                mu[i], std[i], used[i] = fit['expected_demand'], fit['demand_std'], len(series)
        totals = np.bincount(codes[valid], weights=self.totals[valid], minlength=len(unique))
        sizes = np.bincount(codes[valid], minlength=len(unique))
        available = valid.copy(); available[valid] &= np.isfinite(mu[codes[valid]])
        idx = np.flatnonzero(available); group = codes[idx]
        shares = (self.totals[idx] + self.prior) / (totals[group] + sizes[group] * self.prior)
        weekly = shares * mu[group]; weekly_std = np.sqrt(shares) * std[group]
        result = pd.DataFrame([self.pairs[i] for i in idx], columns=['Product No', 'Store'])
        result['weekly_expected_demand'] = weekly; result['daily_expected_demand'] = weekly / 7
        result['four_week_expected_demand'] = weekly * 4
        result['demand_std'] = weekly_std
        result['lower_bound_95'] = np.maximum(0, weekly - 1.96 * weekly_std)
        result['upper_bound_95'] = weekly + 1.96 * weekly_std
        result['daily_lower_bound'] = np.maximum(0, weekly / 7 - 1.96 * weekly_std / np.sqrt(7))
        result['daily_upper_bound'] = weekly / 7 + 1.96 * weekly_std / np.sqrt(7)
        result['information_cutoff'] = cutoff; result['forecast_start_date'] = cutoff + pd.Timedelta(days=1)
        result['history_days'] = 0 if self.first is None else (cutoff - self.first).days + 1
        result['source_history_end'] = self.last; result['source_history_start'] = self.first
        result['completed_weeks_used'] = used[group]
        result['method'] = self.method; result['aggregate_level'] = 'Product Subcategory x Store'
        result['uncertainty_label'] = 'normal approximation; not calibrated; independent-day scaling assumed'
        result['forecast_unit'] = 'units per day'; result['aggregate_forecast_unit'] = 'units per week'
        result['demand_input'] = 'estimated_demand'; result['demand_share'] = shares
        result['aggregate_expected_weekly_demand'] = mu[group]
        return result
