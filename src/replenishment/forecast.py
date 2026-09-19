"""Transparent forecasts from released requests, never fulfilled-sales proxies."""
from collections import defaultdict
from datetime import date, timedelta
from math import floor

from src.demo_data.utils import date_range
from .contracts import Demand, ForecastBundle, PlannerSettings, PlanningSnapshot

METHODS = ('mean4', 'mean8', 'weekday8')


def daily_estimates(state: PlanningSnapshot, cutoff: date, days: list[date], method: str) -> dict:
    """Estimate due-date demand; no unfinished/future historical day is used."""
    if method not in METHODS:
        raise ValueError('Unknown forecasting method')
    window = 28 if method == 'mean4' else 56
    start = cutoff - timedelta(days=window)
    totals = defaultdict(float)
    for line in state.demand.values():
        if not line.estimated and line.created < cutoff and start <= line.due < cutoff:
            totals[(line.product, line.due.weekday())] += line.units
    result = {}
    for product in state.products:
        average = sum(totals[product, w] for w in range(5)) / (window / 7 * 5)
        for day in days:
            value = totals[product, day.weekday()] / (window / 7) if method == 'weekday8' else average
            result[product, day] = value if day.weekday() < 5 else 0.0
    return result


def historical_scores(state: PlanningSnapshot) -> dict:
    """Eight nonoverlapping weekly targets, each predicted from earlier records."""
    after = state.day + timedelta(days=1)
    end = after - timedelta(days=after.weekday())
    scores = {}
    for method in METHODS:
        absolute, bias, errors = 0.0, 0.0, defaultdict(list)
        for offset in range(8, 0, -1):
            start = end - timedelta(weeks=offset)
            days = list(date_range(start, start + timedelta(days=6)))
            estimate = daily_estimates(state, start, days, method)
            for product in state.products:
                actual = sum(d.units for d in state.demand.values() if not d.estimated and d.product == product
                             and start <= d.due <= days[-1] and d.created <= state.day)
                error = sum(estimate[product, d] for d in days) - actual
                absolute += abs(error)
                bias += error
                errors[product].append(abs(error))
        scores[method] = dict(absolute_unit_error=absolute, signed_unit_error=bias,
                              mean_weekly_product_error={p: sum(v)/len(v) for p, v in errors.items()})
    return scores


def select_method(states: list[PlanningSnapshot]) -> tuple[str, dict]:
    """Select a shared method by summed weekly absolute error; stable simpler ties."""
    scores = {method: 0.0 for method in METHODS}
    reports = []
    for state in states:
        report = historical_scores(state)
        reports.append(report)
        for method in METHODS:
            scores[method] += report[method]['absolute_unit_error']
    best = min(METHODS, key=lambda m: (round(scores[m], 8), METHODS.index(m)))
    return best, dict(totals=scores, per_history=reports)


def forecast(state: PlanningSnapshot, settings: PlannerSettings) -> ForecastBundle:
    """Return nominal demand and observed error magnitudes, not calibrated intervals."""
    days = list(date_range(state.day, state.day + timedelta(days=settings.horizon_days-1)))
    daily = daily_estimates(state, state.day, days, settings.forecast_method)
    daily = {k: v * settings.demand_multiplier for k, v in daily.items()}
    warnings = []
    start = state.day - timedelta(days=56)
    for product in state.products:
        count = sum(1 for d in state.demand.values() if d.product == product and start <= d.created < state.day)
        if count < 8:
            warnings.append(f'{product}: sparse requests; demand projections are uncertain')
    if state.promotions:
        warnings.append('Announced promotions require review; no hidden promotion uplift applied')
    errors = historical_scores(state)[settings.forecast_method]['mean_weekly_product_error']
    return ForecastBundle(settings.forecast_method, daily, errors, warnings)


def projected_requests(state: PlanningSnapshot, bundle: ForecastBundle) -> list[Demand]:
    """Create labelled planning cohorts for only the unbooked forecast remainder.

    Carry fractional units across dates and allocate integer remainders by known
    customer request shares. Real booked customer lines are never changed.
    """
    if bundle.pattern is not None:
        from .patterns import pattern_remainder
        return pattern_remainder(state, bundle.pattern)
    booked, shares = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for line in state.demand.values():
        if line.remaining:
            booked[line.product, max(state.day, line.due)] += line.remaining
        if not line.estimated and line.created < state.day and line.created >= state.day - timedelta(days=56):
            shares[line.product][line.customer] += line.units
    output = []
    for product in sorted(state.products):
        cumulative, allocated = 0.0, 0
        customer_allocated = defaultdict(int)
        weights = shares[product]
        if not weights:
            continue
        total_weight = sum(weights.values())
        for (pid, day), estimate in sorted(bundle.daily.items()):
            if pid != product or day < state.day:
                continue
            cumulative += max(0.0, estimate - booked[pid, day])
            units = floor(cumulative + 1e-9) - allocated
            allocated += units
            if units:
                # Keep one daily product cohort intact rather than pretending
                # every customer places a tiny order every day. Rotate its
                # customer by the greatest deficit against recorded unit shares.
                customer = max(sorted(weights), key=lambda c: allocated * weights[c]/total_weight - customer_allocated[c])
                customer_allocated[customer] += units
                output.append(Demand(f'EST-{product}-{day}-{customer}', product, customer, state.day,
                                     day, units, estimated=True))
    return output
