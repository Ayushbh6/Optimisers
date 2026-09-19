"""Reject inconsistent operational records before forecasting or solver invocation."""
from datetime import date
from math import isfinite
from src.replenishment.contracts import PlanRequest, PlanningSnapshot
from src.replenishment.forecast import METHODS


def validate_state(state: PlanningSnapshot) -> list[str]:
    """Return precise input errors without inventing or repairing business records."""
    errors = []

    def integer(value, minimum, name):
        valid = type(value) is int and value >= minimum
        if not valid:
            errors.append(f'{name}: integer >= {minimum} required')
        return valid

    def dated(value, name):
        valid = type(value) is date
        if not valid:
            errors.append(f'{name}: calendar date required')
        return valid

    if not dated(state.day, 'decision date'):
        return errors
    if state.request_history_start is not None:
        if dated(state.request_history_start, 'request history start') and state.request_history_start > state.day:
            errors.append('Request history coverage cannot begin in the future')
    integer(state.budget_cents, 0, 'new-order allowance cents')
    integer(state.week_spend, 0, 'already committed cents')
    integer(state.capacity_ml, 1, 'warehouse capacity ml')
    for label, collection in (('product', state.products), ('supplier', state.suppliers),
                              ('customer', state.customers), ('lot', state.lots),
                              ('customer line', state.demand), ('supplier line', state.incoming)):
        for key, row in collection.items():
            if not isinstance(key, str) or not key or key != row.id:
                errors.append(f'{label} {key!r}: record identity must match its nonempty mapping key')
    for product in state.products.values():
        integer(product.case, 1, f'{product.id} case size')
        integer(product.volume_ml, 1, f'{product.id} storage ml')
        integer(product.shelf_days, 1, f'{product.id} normal shelf-life days')
    for supplier in state.suppliers.values():
        if integer(supplier.weekday, 0, f'{supplier.id} order weekday') and supplier.weekday > 4:
            errors.append(f'{supplier.id}: ordering requires a weekday from 0 to 4')
        integer(supplier.lead_days, 1, f'{supplier.id} lead working days')
        integer(supplier.minimum_cents, 0, f'{supplier.id} minimum order value cents')
        integer(supplier.fee_cents, 0, f'{supplier.id} delivery charge cents')
    for customer in state.customers.values():
        if type(customer.partial) is not bool:
            errors.append(f'{customer.id}: partial-delivery permission must be a boolean')
        integer(customer.late_days, 0, f'{customer.id} permitted lateness days')
        integer(customer.freshness_days, 0, f'{customer.id} required freshness days')
    term_groups = {}
    for term in state.terms:
        label = f'{term.supplier}/{term.product}'
        if term.supplier not in state.suppliers or term.product not in state.products:
            errors.append(f'{label}: unknown supplier/product in terms')
        integer(term.cost, 1, f'{label} purchase cost cents')
        integer(term.minimum, 1, f'{label} minimum units')
        start_valid = dated(term.start, f'{label} terms start')
        end_valid = term.end is None or dated(term.end, f'{label} terms end')
        if start_valid and end_valid:
            if term.end is not None and term.end < term.start:
                errors.append(f'{label}: terms end precedes start')
            term_groups.setdefault((term.supplier, term.product), []).append(term)
    for pair, terms in term_groups.items():
        ordered = sorted(terms, key=lambda term: term.start)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.end is None or previous.end >= current.start:
                errors.append(f'{pair[0]}/{pair[1]}: overlapping commercial terms')
    for lot in state.lots.values():
        valid_units = integer(lot.units, 0, f'{lot.id} stock units')
        integer(lot.cost, 1, f'{lot.id} acquisition cost cents')
        if lot.product not in state.products:
            errors.append(f'{lot.id}: unknown product')
        if dated(lot.received, f'{lot.id} receipt date') and lot.received > state.day:
            errors.append(f'{lot.id}: receipt is not yet known')
        if dated(lot.expiry, f'{lot.id} expiry date') and valid_units and lot.units and lot.expiry <= state.day:
            errors.append(f'{lot.id}: expired positive stock requires a recorded write-off before planning')
    for line in state.demand.values():
        if line.customer not in state.customers or line.product not in state.products:
            errors.append(f'{line.id}: unknown customer/product')
        checks = [integer(getattr(line, name), 1 if name == 'units' else 0, f'{line.id} {name}')
                  for name in ('units', 'shipped', 'cancelled', 'on_time')]
        created_valid = dated(line.created, f'{line.id} request creation date')
        due_valid = dated(line.due, f'{line.id} due date')
        if type(line.estimated) is not bool:
            errors.append(f'{line.id}: estimated-demand label must be a boolean')
        if created_valid and line.created > state.day:
            errors.append(f'{line.id}: future request is not operational knowledge')
        if created_valid and due_valid and (line.due < line.created or line.due.weekday() >= 5):
            errors.append(f'{line.id}: invalid requested delivery date')
        if all(checks) and (line.remaining < 0 or line.on_time > line.shipped):
            errors.append(f'{line.id}: customer quantities do not reconcile')
    for line in state.incoming.values():
        if line.supplier not in state.suppliers or line.product not in state.products:
            errors.append(f'{line.id}: unknown supplier/product in incoming order')
        integer(line.cost, 1, f'{line.id} agreed cost cents')
        checks = [integer(getattr(line, name), 1 if name == 'units' else 0, f'{line.id} {name}')
                  for name in ('units', 'received', 'cancelled')]
        placed_valid = dated(line.placed, f'{line.id} purchase date')
        if placed_valid and line.placed > state.day:
            errors.append(f'{line.id}: future supplier order is not operational knowledge')
        if line.expected is not None and dated(line.expected, f'{line.id} expected receipt date'):
            if placed_valid and line.expected < line.placed:
                errors.append(f'{line.id}: expected receipt precedes purchase')
        if all(checks) and line.remaining < 0:
            errors.append(f'{line.id}: supplier quantities do not reconcile')
    if not errors:
        occupied = sum(lot.units*state.products[lot.product].volume_ml for lot in state.lots.values())
        if occupied > state.capacity_ml:
            errors.append('Opening stock exceeds declared storage capacity')
    return errors


def validate_request(request: PlanRequest) -> None:
    """Validate buyer assumptions as well as the business records they act upon."""
    errors = validate_state(request.snapshot)
    settings = request.settings
    for name, minimum, maximum in (('horizon_days', 1, 56), ('safety_workdays', 0, None),
                                   ('delay_workdays', 0, None), ('incoming_freshness_days', 1, 365)):
        value = getattr(settings, name)
        if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
            errors.append(f'{name}: integer >= {minimum}' + (f' and <= {maximum}' if maximum is not None else '') + ' required')
    for name, positive in (('demand_multiplier', False), ('solve_seconds', True)):
        value = getattr(settings, name)
        if type(value) not in (int, float) or not isfinite(value) or value < 0 or (positive and value == 0):
            errors.append(f'{name}: finite {"positive" if positive else "nonnegative"} number required')
    if settings.forecast_method not in METHODS:
        errors.append('Unknown forecasting method')
    for product in request.excluded:
        if product not in request.snapshot.products:
            errors.append(f'Unknown excluded product: {product}')
    for product, units in request.locks.items():
        if product not in request.snapshot.products:
            errors.append(f'Unknown locked product: {product}')
        else:
            case = request.snapshot.products[product].case
            if type(units) is not int or units < 0 or type(case) is not int or case <= 0 or units % case:
                errors.append(f'{product}: locked units must be nonnegative whole cases')
        if units and product in request.excluded:
            errors.append(f'{product}: cannot both exclude and lock a purchase')
    if errors:
        raise ValueError('; '.join(errors))
