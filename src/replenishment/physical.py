"""Shared physical rules; hidden events are supplied by callers, never read here."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta

from src.demo_data.utils import add_workdays
from .contracts import Demand, Incoming, Lot, PlanningSnapshot, Purchase


def used_volume(state: PlanningSnapshot) -> int:
    """Occupied sale-unit volume, including stock ineligible for customers."""
    return sum(l.units * state.products[l.product].volume_ml for l in state.lots.values())


def validate_purchases(state: PlanningSnapshot, purchases: list[Purchase]) -> list[str]:
    """Independently check today's basket before creating any commitments."""
    if not purchases:
        return []  # Reducing an allowance cannot undo money already committed.
    errors, seen, supplier_value = [], set(), defaultdict(int)
    for p in purchases:
        key = (p.supplier, p.product)
        if key in seen:
            errors.append(f'Duplicate purchase line: {key}')
        seen.add(key)
        if p.day != state.day or p.supplier not in state.suppliers or p.product not in state.products:
            errors.append(f'Invalid date or identity: {key}')
            continue
        if type(p.units) is not int or p.units <= 0:
            errors.append(f'Positive integer units required: {key}')
            continue
        supplier, product = state.suppliers[p.supplier], state.products[p.product]
        if p.day.weekday() != supplier.weekday:
            errors.append(f'Supplier is closed for ordering: {p.supplier}')
        try:
            term = state.term(p.supplier, p.product)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if p.units % product.case or p.units < term.minimum:
            errors.append(f'Case/minimum quantity violation: {p.product}')
        supplier_value[p.supplier] += p.units * term.cost
    for supplier, value in supplier_value.items():
        if value < state.suppliers[supplier].minimum_cents:
            errors.append(f'Supplier minimum value not met: {supplier}')
    spend = sum(supplier_value.values()) + sum(state.suppliers[s].fee_cents for s in supplier_value)
    if state.week_spend + spend > state.budget_cents:
        errors.append('Weekly new-order allowance exceeded')
    return errors


class Operations:
    """Mutable private copy of public state with independently auditable movements."""
    def __init__(self, state: PlanningSnapshot):
        self.state = deepcopy(state)
        self.opening = {k: l.units for k, l in state.lots.items()}
        self.movements: list[dict] = []
        self.deliveries: list[dict] = []
        self.cancellations: list[dict] = []
        self.orders: list[dict] = []
        self.balances: list[dict] = []
        self.initial_demand = {k: (d.shipped, d.cancelled) for k, d in state.demand.items()}
        self.initial_incoming = {k: (p.received, p.cancelled) for k, p in state.incoming.items()}
        self.initial_line_ids = {k for k, d in state.demand.items() if d.remaining}
        self.initial_day = state.day
        self.initial_week_spend = state.week_spend
        self.counter = max([0] + [int(k.rsplit('-', 1)[-1]) for k in
                           list(state.lots)+list(state.incoming)
                           if k.startswith(('R-LOT-', 'R-POL-')) and k.rsplit('-', 1)[-1].isdigit()])

    def move(self, lot: Lot, quantity: int, kind: str, source: str) -> None:
        lot.units += quantity
        if lot.units < 0:
            raise AssertionError('Negative physical stock')
        self.movements.append(dict(day=str(self.state.day), lot=lot.id, quantity=quantity,
                                   kind=kind, source=source, cost=lot.cost))

    def begin_day(self, day: date) -> None:
        """Expiry precedes notices and receipts every calendar day."""
        if day <= self.state.day:
            raise ValueError('Physical clock must advance')
        previous_week = self.state.day-timedelta(days=self.state.day.weekday())
        self.state.day = day
        if day-timedelta(days=day.weekday()) != previous_week:
            self.state.week_spend = 0
        for lot in self.state.lots.values():
            if lot.units and lot.expiry <= day:
                self.move(lot, -lot.units, 'expiry', lot.id)

    def add_demand(self, line: Demand) -> None:
        if line.id in self.state.demand or line.created != self.state.day:
            raise ValueError('Duplicate or unreleased customer request')
        self.state.demand[line.id] = deepcopy(line)

    def receive(self, line_id: str, quantity: int, expiry: date) -> int:
        """Accept available capacity; return the explicitly undelivered balance."""
        if self.state.day.weekday() >= 5:
            raise ValueError('Receipts require a working day')
        incoming = self.state.incoming[line_id]
        if not 0 < quantity <= incoming.remaining:
            raise ValueError('Receipt exceeds outstanding supplier units')
        product = self.state.products[incoming.product]
        accepted = min(quantity, max(0, (self.state.capacity_ml - used_volume(self.state)) // product.volume_ml))
        if accepted:
            self.counter += 1
            lot = Lot(f'R-LOT-{self.counter}', product.id, self.state.day, expiry, incoming.cost, 0)
            self.state.lots[lot.id] = lot
            incoming.received += accepted
            self.move(lot, accepted, 'receipt', line_id)
            # Already expired deliveries cannot persist until tomorrow's expiry step.
            if expiry <= self.state.day:
                self.move(lot, -accepted, 'expiry', lot.id)
        return quantity - accepted

    def place(self, purchases: list[Purchase]) -> list[Incoming]:
        """Create validated orders. Actual delivery scheduling belongs to the caller."""
        errors = validate_purchases(self.state, purchases)
        if errors:
            raise ValueError('; '.join(errors))
        if any(o['day'] == str(self.state.day) and o['supplier'] in {p.supplier for p in purchases} for o in self.orders):
            raise ValueError('A supplier basket for this date has already been committed')
        created, charged = [], set()
        for purchase in purchases:
            self.counter += 1
            supplier = self.state.suppliers[purchase.supplier]
            term = self.state.term(purchase.supplier, purchase.product)
            order_id = f'R-PO-{self.state.day}-{purchase.supplier}'
            if purchase.supplier not in charged:
                self.state.week_spend += supplier.fee_cents
                self.orders.append(dict(day=str(self.state.day), supplier=supplier.id,
                                        fee_cents=supplier.fee_cents, order=order_id))
                charged.add(purchase.supplier)
            self.state.week_spend += purchase.units * term.cost
            line = Incoming(f'R-POL-{self.counter}', order_id, supplier.id, purchase.product,
                            self.state.day, add_workdays(self.state.day, supplier.lead_days),
                            purchase.units, term.cost)
            self.state.incoming[line.id] = line
            created.append(line)
        return created

    def finish_day(self) -> None:
        """Dispatch due lines using customer rules, then cancel expired obligations."""
        state, day = self.state, self.state.day
        if day.weekday() < 5:
            lines = sorted((d for d in state.demand.values() if d.remaining and d.due <= day),
                           key=lambda d: (d.due, d.created, d.id))
            for line in lines:
                customer = state.customers[line.customer]
                if day > add_workdays(line.due, customer.late_days):
                    continue
                lots = sorted((l for l in state.lots.values() if l.product == line.product and l.units
                               and l.expiry > day and l.expiry >= day + timedelta(days=customer.freshness_days)),
                              key=lambda l: (l.expiry, l.received, l.id))
                available = sum(l.units for l in lots)
                if not customer.partial and available < line.remaining:
                    continue
                remaining = min(available, line.remaining)
                for lot in lots:
                    quantity = min(remaining, lot.units)
                    if not quantity:
                        break
                    self.move(lot, -quantity, 'shipment', line.id)
                    line.shipped += quantity
                    line.on_time += quantity if day <= line.due else 0
                    self.deliveries.append(dict(day=str(day), line=line.id, lot=lot.id, units=quantity))
                    remaining -= quantity
        for line in state.demand.values():
            if line.remaining and day >= add_workdays(line.due, state.customers[line.customer].late_days):
                self.cancellations.append(dict(day=str(day), line=line.id, units=line.remaining))
                line.cancelled += line.remaining
        self.balances.append(dict(day=str(day), stock_cents=sum(l.units*l.cost for l in state.lots.values()),
                                 incoming_cents=sum(p.remaining*p.cost for p in state.incoming.values()),
                                 volume_ml=used_volume(state)))

    def audit(self) -> list[str]:
        """Reconcile independent journals against final lots and obligations."""
        errors, balances = [], defaultdict(int, self.opening)
        received, shipped, cancelled = defaultdict(int), defaultdict(int), defaultdict(int)
        for movement in self.movements:
            balances[movement['lot']] += movement['quantity']
            if balances[movement['lot']] < 0:
                errors.append('Negative journal balance')
            if movement['kind'] == 'receipt':
                received[movement['source']] += movement['quantity']
            elif movement['kind'] == 'shipment':
                shipped[movement['source']] -= movement['quantity']
        for row in self.cancellations:
            cancelled[row['line']] += row['units']
        for key, lot in self.state.lots.items():
            if balances[key] != lot.units:
                errors.append(f'Lot balance mismatch: {key}')
        for key, line in self.state.demand.items():
            old_ship, old_cancel = self.initial_demand.get(key, (0, 0))
            if line.shipped != old_ship + shipped[key] or line.cancelled != old_cancel + cancelled[key] or line.remaining < 0:
                errors.append(f'Customer reconciliation: {key}')
        for key, line in self.state.incoming.items():
            old_received, old_cancel = self.initial_incoming.get(key, (0, 0))
            if line.received != old_received + received[key] or line.cancelled != old_cancel or line.remaining < 0:
                errors.append(f'Supplier reconciliation: {key}')
        if any(b['volume_ml'] > self.state.capacity_ml for b in self.balances):
            errors.append('Capacity exceeded')
        # Recalculate weekly purchasing from immutable order-line obligations
        # and separately recorded supplier charges, not the spend accumulator.
        spend = defaultdict(int)
        initial_week = self.initial_day-timedelta(days=self.initial_day.weekday())
        spend[initial_week] = self.initial_week_spend
        for key, line in self.state.incoming.items():
            if key in self.initial_incoming:
                continue
            week = line.placed-timedelta(days=line.placed.weekday())
            spend[week] += line.units*line.cost
        for order in self.orders:
            day = date.fromisoformat(order['day'])
            spend[day-timedelta(days=day.weekday())] += order['fee_cents']
        current_week = self.state.day-timedelta(days=self.state.day.weekday())
        if self.state.week_spend != spend[current_week]:
            errors.append('Purchasing spend accumulator does not reconcile')
        for week, value in spend.items():
            allowance = max(self.state.budget_cents, self.initial_week_spend) if week == initial_week else self.state.budget_cents
            if value > allowance:
                errors.append(f'Weekly budget exceeded: {week}')
        return errors
