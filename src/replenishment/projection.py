"""Conditional projections from public state; no evaluator imports allowed."""
from copy import deepcopy
from datetime import date, timedelta

from src.demo_data.utils import add_workdays, date_range
from .contracts import PlannerSettings, PlanningSnapshot, Purchase
from .forecast import forecast, projected_requests
from .physical import Operations


def metrics(operations: Operations, start: date, end: date, *, initial_ids: set[str] | None = None) -> dict:
    """Keep service, stock investment and cash expenditure separate."""
    state = operations.state
    selected = [d for d in state.demand.values() if start <= d.created <= end or d.id in (initial_ids or set())]
    requested = sum(d.units for d in selected)
    balances = [b for b in operations.balances if str(start) <= b['day'] <= str(end)]
    denominator = max(1, len(balances))
    expiry = -sum(m['quantity']*m['cost'] for m in operations.movements
                  if m['kind'] == 'expiry' and str(start) <= m['day'] <= str(end))
    orders = [p for p in state.incoming.values() if start <= p.placed <= end]
    end_balance = balances[-1] if balances else dict(stock_cents=0, incoming_cents=0)
    return dict(requested_units=requested, on_time_units=sum(d.on_time for d in selected),
                service=sum(d.on_time for d in selected)/requested if requested else 1.0,
                complete_line_service=sum(d.on_time == d.units for d in selected)/len(selected) if selected else 1.0,
                shipped_units=sum(d.shipped for d in selected), late_units=sum(d.shipped-d.on_time for d in selected),
                cancelled_units=sum(d.cancelled for d in selected), open_units=sum(d.remaining for d in selected),
                average_stock_cents=sum(b['stock_cents'] for b in balances)/denominator,
                average_incoming_cents=sum(b['incoming_cents'] for b in balances)/denominator,
                investment_cents=sum(b['stock_cents']+b['incoming_cents'] for b in balances)/denominator,
                expiry_cents=expiry, ending_investment_cents=end_balance['stock_cents']+end_balance['incoming_cents'],
                purchase_cents=sum(p.units*p.cost for p in orders),
                fees_cents=sum(o['fee_cents'] for o in operations.orders if str(start) <= o['day'] <= str(end)))


def project(state: PlanningSnapshot, settings: PlannerSettings, purchases: list[Purchase], *, bundle=None, policy=None, add_estimates=True) -> Operations:
    """Replay a complete dated proposal with the same physical dispatch as evaluation."""
    bundle = bundle or forecast(state, settings)
    public = deepcopy(state)
    if add_estimates:
        for line in projected_requests(state, bundle):
            public.demand[line.id] = line
    operations = Operations(public)
    scheduled = []
    for line in public.incoming.values():
        # Receiving has already occurred at the current decision time.
        if line.remaining and line.expected and line.expected > state.day:
            arrival = add_workdays(line.expected, settings.delay_workdays)
            scheduled.append((arrival, line.id, line.remaining,
                              arrival + timedelta(days=settings.incoming_freshness_days)))
    end = state.day + timedelta(days=settings.horizon_days-1)
    for day in date_range(state.day, end):
        if day > state.day:
            operations.begin_day(day)
        due = [d for d in scheduled if d[0] == day]
        scheduled = [d for d in scheduled if d[0] != day]
        for arrival, key, quantity, expiry in due:
            left = operations.receive(key, quantity, expiry)
            if left:
                scheduled.append((add_workdays(day, 1), key, left, expiry))
        today = policy(operations.state, bundle) if policy is not None else [p for p in purchases if p.day == day]
        for line in operations.place(today):
            arrival = add_workdays(line.expected, settings.delay_workdays)
            scheduled.append((arrival, line.id, line.units, arrival + timedelta(days=settings.incoming_freshness_days)))
        operations.finish_day()
    errors = operations.audit()
    if errors:
        raise AssertionError(errors)
    return operations


def planning_metrics(operations: Operations, anchor: PlanningSnapshot, settings: PlannerSettings) -> dict:
    """Incremental service on open units, excluding pre-decision fulfilment."""
    end = anchor.day + timedelta(days=settings.horizon_days-1)
    result = metrics(operations, anchor.day, end, initial_ids=operations.initial_line_ids)
    requested = on_time = booked_fulfilled = booked_units = 0
    for key, line in operations.state.demand.items():
        old = anchor.demand.get(key)
        if old is not None and old.remaining:
            requested += old.remaining
            on_time += line.on_time-old.on_time
            booked_units += old.remaining
            booked_fulfilled += line.shipped-old.shipped
        elif line.estimated and old is None:
            requested += line.units
            on_time += line.on_time
    result.update(requested_units=requested, on_time_units=on_time,
                  service=on_time/requested if requested else 1.0,
                  booked_fulfilled_units=booked_fulfilled, booked_units=booked_units)
    return result
