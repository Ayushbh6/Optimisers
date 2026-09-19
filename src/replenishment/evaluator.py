"""Private future-event harness. This module must never be imported by a planner.

The evaluator owns actual delivery schedules. Its only planner input is a copied
PlanningSnapshot after today's notices, receipts and customer requests release.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, timedelta
from math import floor
from pathlib import Path
import sqlite3

from src.demo_data.schema import connect
from src.demo_data.utils import add_workdays, date_range
from .contracts import Demand, PlannerSettings, PlanRequest
from .physical import Operations
from .projection import metrics
from .state import load_snapshot


class World:
    """Keep future requests, actual supply and notices outside public state."""
    def __init__(self, folder: Path, *, delay_days: int = 0, freshness_days: int | None = None):
        self.folder, self.delay_days, self.freshness_days = folder, delay_days, freshness_days
        with connect(folder/'evaluator.sqlite', readonly=True) as db:
            headers = {r['customer_order_id']: dict(r) for r in db.execute('SELECT * FROM future_customer_orders')}
            self.requests = defaultdict(list)
            for r in db.execute('SELECT * FROM future_customer_order_lines'):
                h = headers[r['customer_order_id']]
                created = date.fromisoformat(h['created_date'])
                self.requests[created].append(Demand(r['customer_order_line_id'], r['product_id'], h['customer_id'],
                    created, date.fromisoformat(h['due_date']), r['requested_units']))
            self.conditions = {(r['supplier_id'], date.fromisoformat(r['start_date'])):
                               (r['delay_workdays']+delay_days, r['fill_rate_basis_points'])
                               for r in db.execute('SELECT * FROM future_supplier_conditions')}
            self.pending = []
            for r in db.execute('SELECT * FROM continuation_deliveries ORDER BY delivery_id'):
                arrival = add_workdays(date.fromisoformat(r['arrival_date']), delay_days)
                expiry = date.fromisoformat(r['expiry_date'])
                if freshness_days is not None:
                    expiry = min(expiry, arrival+timedelta(days=freshness_days))
                self.pending.append(dict(day=arrival, line=r['supplier_order_line_id'],
                                         units=r['quantity_units'], expiry=expiry))
            self.notices = []
            for r in db.execute('SELECT * FROM continuation_notices'):
                item = dict(r)
                if item['revised_expected_date'] and delay_days:
                    item['revised_expected_date'] = str(add_workdays(date.fromisoformat(item['revised_expected_date']), delay_days))
                self.notices.append(item)

    def release(self, op: Operations) -> None:
        """Release only today's events, with explicit remaining deliveries."""
        day = op.state.day
        for notice in self.notices:
            if notice['known_at'] == str(day):
                op.state.notices.append(notice.copy())
                if notice['revised_expected_date']:
                    for incoming in op.state.incoming.values():
                        if incoming.order == notice['supplier_order_id']:
                            incoming.expected = date.fromisoformat(notice['revised_expected_date'])
        self.notices = [n for n in self.notices if n['known_at'] > str(day)]
        due = [p for p in self.pending if p['day'] == day]
        self.pending = [p for p in self.pending if p['day'] != day]
        for event in due:
            left = op.receive(event['line'], event['units'], event['expiry'])
            if left:
                retry = add_workdays(day, 1)
                self.pending.append({**event, 'day': retry, 'units': left})
                incoming = op.state.incoming[event['line']]
                incoming.expected = retry
                op.state.notices.append(dict(known_at=str(day), supplier_order_id=incoming.order,
                    update_type='capacity_rejection', affected_units=left, revised_expected_date=str(retry)))
        for line in self.requests.get(day, []):
            op.add_demand(line)

    def schedule(self, op: Operations, incoming) -> None:
        """Respond by supplier and promised date, independent of policy call order."""
        day = op.state.day
        delay, fill = self.conditions[incoming.supplier, incoming.expected]
        arrival = add_workdays(incoming.expected, delay)
        expiry = incoming.expected+timedelta(days=op.state.products[incoming.product].shelf_days-14)
        if self.freshness_days is not None:
            expiry = min(expiry, arrival+timedelta(days=self.freshness_days))
        first = max(1, floor(incoming.units*fill/10000))
        self.pending.append(dict(day=arrival, line=incoming.id, units=first, expiry=expiry))
        if delay:
            self.notices.append(dict(known_at=str(incoming.expected), supplier_order_id=incoming.order,
                                     update_type='delay', revised_expected_date=str(arrival)))
        if first < incoming.units:
            second = add_workdays(arrival, 2)
            self.pending.append(dict(day=second, line=incoming.id, units=incoming.units-first, expiry=expiry))
            self.notices.append(dict(known_at=str(arrival), supplier_order_id=incoming.order,
                                     update_type='partial_delivery', revised_expected_date=str(second)))


def run_policy(folder: Path, settings: PlannerSettings, method: str, *, delay_days=0, freshness_days=None) -> dict:
    """Evaluate one independently evolving policy and reconcile all events."""
    from .baseline import order_today
    from .planner import plan
    world = World(folder, delay_days=delay_days, freshness_days=freshness_days)
    with connect(folder/'operational.sqlite', readonly=True) as db:
        manifest = dict(db.execute('SELECT key, value FROM dataset_manifest'))
    anchor = date.fromisoformat(manifest['history_end'])
    start, end = anchor+timedelta(days=1), anchor+timedelta(weeks=8)
    op = Operations(load_snapshot(folder/'operational.sqlite', anchor))
    decisions = []
    for day in date_range(start, end+timedelta(days=30)):
        op.begin_day(day)
        if day.weekday() < 5:
            world.release(op)
        if day <= end and any(s.weekday == day.weekday() for s in op.state.suppliers.values()):
            if method == 'baseline':
                purchases = order_today(op.state, settings)
                decision = dict(day=str(day), method=method)
            elif method == 'optimiser':
                result = plan(PlanRequest(op.state, settings))
                chosen = next(a for a in result.alternatives if a.name == result.recommended)
                purchases = [p for p in chosen.purchases if p.day == day]
                if result.recommended == 'Stock-cover comparison':
                    comparison = order_today(op.state, settings)
                    normalise = lambda rows: sorted((p.supplier, p.product, p.units) for p in rows)
                    if normalise(purchases) != normalise(comparison):
                        raise AssertionError('Baseline fallback differs from comparison at identical decision state')
                decision = dict(day=str(day), recommended=result.recommended, warnings=result.warnings,
                    input_hash=result.input_hash, version=result.version, sensitivity=result.sensitivity,
                    alternatives=[dict(name=a.name, status=a.status, metrics=a.metrics, reasons=a.reasons)
                                  for a in result.alternatives])
            else:
                raise ValueError('Unknown policy')
            decision['purchases'] = [asdict(p) for p in purchases]
            decisions.append(decision)
            for incoming in op.place(purchases):
                world.schedule(op, incoming)
        op.finish_day()
        if day == end:
            primary = metrics(op, start, end)
    errors = op.audit()
    settlement = metrics(op, start, end)
    # Costs and investment refer to the primary trading interval; final service
    # includes resolution of requests created before its end.
    breakdown = {}
    for key in ('product', 'customer'):
        groups = defaultdict(list)
        for line in op.state.demand.values():
            if start <= line.created <= end:
                groups[getattr(line, key)].append(line)
        breakdown[key] = {g: dict(requested=sum(d.units for d in lines),
            on_time=sum(d.on_time for d in lines), shipped=sum(d.shipped for d in lines),
            cancelled=sum(d.cancelled for d in lines), open=sum(d.remaining for d in lines)) for g, lines in groups.items()}
    return dict(method=method, settings=asdict(settings), primary=primary, settled=settlement,
        settlement_end=str(op.state.day), final_stock_cents=sum(l.units*l.cost for l in op.state.lots.values()),
        final_incoming_cents=sum(p.remaining*p.cost for p in op.state.incoming.values()),
        settlement_expiry_cents=-sum(m['quantity']*m['cost'] for m in op.movements if m['kind']=='expiry' and m['day']>str(end)),
        unresolved_supplier_units=sum(p.remaining for p in op.state.incoming.values()),
        audit_errors=errors, breakdown=breakdown, decisions=decisions)
