"""Demand sensitivity views derived only from observed historical forecast errors."""
from __future__ import annotations

from math import isfinite
from src.replenishment.contracts import ForecastBundle, PlanningSnapshot, PlannerSettings, Purchase


def demand_sensitivities(bundle: ForecastBundle) -> dict[str, ForecastBundle]:
    """Return lower/nominal/higher planning views, not probabilistic guarantees.

    The stored errors are mean absolute weekly forecast errors. Spread one such
    error across five receiving/dispatch weekdays. This is an explicit stress
    magnitude, not an estimated percentile. Customer bookings are not modified;
    the shared forecast-remainder logic still takes booked quantities first.
    """
    if any(not isfinite(v) or v < 0 for v in bundle.errors.values()):
        raise ValueError('Historical weekly error magnitudes must be finite and nonnegative')
    if any(not isfinite(v) or v < 0 for v in bundle.daily.values()):
        raise ValueError('Forecast demand must be finite and nonnegative')
    result = {'nominal': bundle}
    for name, sign in (('lower', -1), ('higher', 1)):
        daily = {(product, day): max(0.0, value+sign*bundle.errors.get(product, 0)/5)
                 if day.weekday()<5 else 0.0 for (product, day), value in bundle.daily.items()}
        result[name] = ForecastBundle(bundle.method, daily, dict(bundle.errors),
            list(bundle.warnings)+[f'{name.capitalize()} demand sensitivity: one observed mean absolute weekly error; not a confidence interval'])
    return result


def compare_views(state: PlanningSnapshot, settings: PlannerSettings,
                  baseline: list[Purchase], proposals: dict[str, list[Purchase]],
                  views: dict[str, ForecastBundle]) -> dict:
    """Challenge fixed proposals equally; never learn from realised future events.

    Both purchase schedules are held fixed within each projection. This is a
    stress check on the proposed plan, not a simulation of later buyer responses.
    Nominal service and cost still come from the shared main projection.
    """
    from src.replenishment.projection import project, planning_metrics
    rows = {}
    for view, forecast_view in views.items():
        if view == 'nominal':
            continue
        reference = planning_metrics(project(state, settings, baseline, bundle=forecast_view), state, settings)
        candidates = {}
        for name, purchases in proposals.items():
            try:
                metrics = planning_metrics(project(state, settings, purchases, bundle=forecast_view), state, settings)
                candidates[name] = dict(metrics=metrics, valid=True,
                    preserves_service=metrics['service'] >= reference['service']-1e-8,
                    preserves_booked=metrics['booked_fulfilled_units'] >= reference['booked_fulfilled_units'])
            except ValueError as exc:
                candidates[name] = dict(valid=False, error=str(exc), preserves_service=False, preserves_booked=False)
        rows[view] = dict(baseline=reference, alternatives=candidates)
    return rows


def compare_sensitivities(state: PlanningSnapshot, settings: PlannerSettings,
                          baseline: list[Purchase], proposals: dict[str, list[Purchase]],
                          bundle: ForecastBundle) -> dict:
    """Keep the existing smooth-error sensitivity interface for callers."""
    return compare_views(state, settings, baseline, proposals, demand_sensitivities(bundle))
