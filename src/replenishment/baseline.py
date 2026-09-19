"""Budget-aware stock cover, respecting complete supplier baskets."""
from collections import defaultdict
from datetime import timedelta
from math import ceil

from src.demo_data.utils import add_workdays, date_range
from .contracts import PlannerSettings, PlanningSnapshot, Purchase
from .forecast import forecast, projected_requests
from .physical import validate_purchases
from .projection import project


def order_today(state: PlanningSnapshot, settings: PlannerSettings, *, bundle=None) -> list[Purchase]:
    """Cover demand through the next replenishment, prioritising booked shortfalls."""
    bundle = bundle or forecast(state, settings)
    # Nested baseline projections already contain the shared demand cohorts.
    # Generating their fractional remainder again changes purchases at the same
    # decision boundary and can overwrite an existing estimated line.
    expanded = any(d.estimated for d in state.demand.values())
    no_buy = project(state, settings, [], bundle=bundle, add_estimates=not expanded)
    candidates = []
    for term in state.terms:
        supplier = state.suppliers[term.supplier]
        if state.day.weekday() != supplier.weekday or state.term(term.supplier, term.product) != term:
            continue
        target_end = add_workdays(state.day, supplier.lead_days + settings.safety_workdays) + timedelta(days=7)
        lines = [d for d in no_buy.state.demand.values() if d.product == term.product and d.due <= target_end
                 and ((d.estimated and d.due >= state.day)
                      or (not d.estimated and d.id in state.demand and state.demand[d.id].remaining))]
        # Subtract cancellations/shipments that existed at the decision boundary.
        gap = sum(d.remaining + d.cancelled - (state.demand[d.id].cancelled if d.id in state.demand else 0)
                  for d in lines)
        if gap <= 0:
            continue
        stock = sum(l.units for l in state.lots.values() if l.product == term.product)
        expected = sum(v for (p, day), v in bundle.daily.items() if p == term.product and day <= target_end)
        booked_short = sum(d.remaining for d in state.demand.values()
                           if not d.estimated and d.product == term.product and d.due <= target_end)
        product = state.products[term.product]
        units = max(term.minimum, ceil(gap/product.case)*product.case)
        candidates.append((-(booked_short > stock), stock/max(expected, 1), term.product, term, units))
    selected, supplier_values = [], defaultdict(int)
    remaining = state.budget_cents - state.week_spend
    for _, _, product_id, term, units in sorted(candidates, key=lambda c: c[:3]):
        supplier = state.suppliers[term.supplier]
        fee = supplier.fee_cents if not supplier_values[term.supplier] else 0
        case = state.products[product_id].case
        affordable = max(0, (remaining-fee)//(term.cost*case))*case
        quantity = min(units, affordable)
        if quantity < term.minimum:
            continue
        selected.append(Purchase(state.day, term.supplier, product_id, quantity))
        remaining -= quantity*term.cost + fee
        supplier_values[term.supplier] += quantity*term.cost
    # If a basket misses the supplier value minimum, add cases to its highest
    # priority demanded product only when affordable. Do not discard a useful
    # order merely because the greedy first pass missed a grouping constraint.
    for supplier_id, value in supplier_values.items():
        if not value:
            continue
        supplier = state.suppliers[supplier_id]
        if value < supplier.minimum_cents:
            index = next(i for i, p in enumerate(selected) if p.supplier == supplier_id)
            line = selected[index]
            term, case = state.term(supplier_id, line.product), state.products[line.product].case
            extra = ceil((supplier.minimum_cents-value)/(term.cost*case))*case
            if extra*term.cost <= remaining:
                selected[index] = Purchase(line.day, line.supplier, line.product, line.units+extra)
                remaining -= extra*term.cost
            else:
                selected = [p for p in selected if p.supplier != supplier_id]
    errors = validate_purchases(state, selected)
    if errors:
        raise AssertionError(errors)
    return selected
