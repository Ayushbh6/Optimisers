"""Historical request-pattern sensitivities, separate from the shared mean forecast."""
from collections import defaultdict
from dataclasses import replace
from datetime import timedelta

from .contracts import Demand, ForecastBundle, PlanningSnapshot


def historical_patterns(state: PlanningSnapshot, nominal: ForecastBundle, *, blocks: int = 4) -> dict[str, ForecastBundle]:
    """Shift four nonoverlapping 28-day histories without changing order sizes.

    These are historical-pattern stress views, not calibrated probabilities or
    named predictions. Only completed, explicitly covered historical windows are
    used. Zero-request periods remain zero; unavailable history is not invented.
    The main forecast stays unchanged. The 28-day shift preserves weekdays.
    """
    if not 1 <= blocks <= 4:
        raise ValueError('Historical-pattern review supports one to four fixed blocks')
    if state.request_history_start is None:
        return {}
    output = {}
    for index in range(1, blocks+1):
        start = state.day-timedelta(days=28*index)
        stop = start+timedelta(days=28)
        if start < state.request_history_start:
            continue
        shift = state.day-start
        name = f'history-{index}'
        requests = []
        source_ids = []
        for row in sorted(state.demand.values(), key=lambda d: (d.due, d.created, d.id)):
            # Requests already booked before the analogous historical decision
            # are represented by today's real bookings, not invented again.
            if row.estimated or not start <= row.created < state.day or not start <= row.due < stop:
                continue
            if row.product not in state.products or row.customer not in state.customers:
                raise ValueError('Historical request references an unknown product or customer')
            requests.append(Demand(f'PAT-{index}-{row.id}', row.product, row.customer,
                                   state.day, row.due+shift, row.units, estimated=True))
            source_ids.append(row.id)
        daily = defaultdict(float)
        for row in requests:
            daily[row.product, row.due] += row.units
        output[name] = ForecastBundle(nominal.method, dict(daily), dict(nominal.errors),
            list(nominal.warnings)+['Historical order-pattern sensitivity; not a probability forecast'],
            pattern=requests, provenance=dict(source_start=str(start), source_end=str(stop-timedelta(days=1)),
                observed_before=str(state.day), source_request_ids=source_ids,
                quantities='Original requested units, including unmet requests; no rescaling or outcome-based selection'))
    return output


def pattern_remainder(state: PlanningSnapshot, pattern: list[Demand]) -> list[Demand]:
    """Keep real bookings and add only the positive product/date pattern remainder."""
    booked = defaultdict(int)
    for row in state.demand.values():
        if row.remaining:
            booked[row.product, max(state.day, row.due)] += row.remaining
    output = []
    seen = set()
    for row in sorted(pattern, key=lambda d: (d.due, d.customer, d.id)):
        if row.id in seen or row.id in state.demand:
            raise ValueError('Historical-pattern identifiers must be unique and separate from operational records')
        seen.add(row.id)
        if not row.estimated or row.created != state.day or row.due < state.day:
            raise ValueError('Historical-pattern rows must be labelled estimates at this decision date')
        if type(row.units) is not int or row.units <= 0 or row.shipped or row.cancelled or row.on_time:
            raise ValueError('Historical-pattern rows require positive unfulfilled integer units')
        if row.product not in state.products or row.customer not in state.customers:
            raise ValueError('Historical pattern references an unknown product/customer')
        key = row.product, row.due
        replaced = min(booked[key], row.units)
        booked[key] -= replaced
        if row.units > replaced:
            output.append(replace(row, units=row.units-replaced))
    return output
