"""Case-order MILP with dated lot flows; shared replay checks its allocation relaxation.

The model may allocate eligible stock differently from physical due-date/FEFO
dispatch. Only replayed service counts for recommendation and evaluation; solver
optimality is a statement about this explicit planning model, not the business.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from math import ceil
from time import monotonic
import warnings

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from src.demo_data.utils import add_workdays, date_range
from .contracts import PlanRequest, Purchase
from .forecast import projected_requests


class LinearModel:
    """Small sparse model builder keeping constraints and objective inspectable."""
    def __init__(self):
        self.low, self.high, self.integer, self.cost = [], [], [], []
        self.rows, self.columns, self.values, self.lower, self.upper = [], [], [], [], []

    def variable(self, low=0, high=np.inf, integer=False, cost=0.0):
        index = len(self.low)
        self.low.append(low); self.high.append(high); self.integer.append(int(integer)); self.cost.append(cost)
        return index

    def constraint(self, coefficients, low=-np.inf, high=np.inf):
        row = len(self.lower)
        for column, value in coefficients.items():
            if value:
                self.rows.append(row); self.columns.append(column); self.values.append(value)
        self.lower.append(low); self.upper.append(high)

    def solve(self, seconds, objective=None):
        matrix = coo_matrix((self.values, (self.rows, self.columns)),
                            shape=(len(self.lower), len(self.low))).tocsc()
        # HiGHS' sparse wrapper requires native 32-bit index arrays.
        matrix.indices = matrix.indices.astype(np.int32)
        matrix.indptr = matrix.indptr.astype(np.int32)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Unrecognized options detected', category=RuntimeWarning)
            return milp(np.array(self.cost if objective is None else objective),
                        integrality=np.array(self.integer), bounds=Bounds(self.low, self.high),
                        constraints=LinearConstraint(matrix, self.lower, self.upper),
                        options={'time_limit': max(0.05, seconds), 'mip_rel_gap': 0.0,
                                 'threads': 1, 'random_seed': 0})


@dataclass
class SupplyLot:
    product: str
    arrival: object
    expiry: object
    cost: int
    fixed: int = 0
    variable: int | None = None
    scale: int = 1


def build_model(request: PlanRequest, bundle, target_service: float, need_bound: dict | None = None) -> tuple:
    """Build one demand view without solving or exposing evaluator records."""
    state, settings = request.snapshot, request.settings
    days = list(date_range(state.day, state.day + timedelta(days=settings.horizon_days-1)))
    model = LinearModel()
    demands = [d for d in state.demand.values() if d.remaining] + projected_requests(state, bundle)
    product_need = defaultdict(int)
    for demand in demands:
        product_need[demand.product] += demand.remaining
    if need_bound is not None:
        for product, quantity in need_bound.items():
            product_need[product] = max(product_need[product], quantity)
    orders, baskets, activation, lots = {}, defaultdict(list), {}, []
    budgets, supply_counts = defaultdict(dict), defaultdict(int)
    for term in state.terms:
        product, supplier = state.products[term.product], state.suppliers[term.supplier]
        for day in days:
            if day.weekday() != supplier.weekday or not (term.start <= day and (term.end is None or day <= term.end)):
                continue
            case = product.case
            # A useful basket never needs more of one product than all projected
            # requirements, its product minimum, or a whole supplier minimum.
            # This bound still permits minimum-value filler products with no demand.
            useful_maximum = max(ceil(product_need[term.product]/case), ceil(term.minimum/case),
                                 ceil(supplier.minimum_cents/(case*term.cost)))
            maximum = min(useful_maximum, state.budget_cents // (case*term.cost))
            q = model.variable(high=maximum, integer=True)
            on = model.variable(high=1, integer=True)
            model.constraint({q: 1, on: -maximum}, high=0)
            model.constraint({q: 1, on: -ceil(term.minimum/case)}, low=0)
            if term.product in request.excluded:
                model.constraint({q: 1}, low=0, high=0)
            if day == state.day and term.product in request.locks:
                value = request.locks[term.product]
                if type(value) is not int or value < 0 or value % case:
                    raise ValueError(f'Locked quantity must be nonnegative whole cases: {term.product}')
                model.constraint({q: case}, low=value, high=value)
            orders[q] = (day, term, case)
            baskets[day, term.supplier].append(q)
            activation[q] = on
            week = day-timedelta(days=day.weekday())
            budgets[week][q] = case*term.cost
            arrival = add_workdays(day, supplier.lead_days+settings.delay_workdays)
            lots.append(SupplyLot(term.product, arrival, arrival+timedelta(days=settings.incoming_freshness_days),
                                  term.cost, variable=q, scale=case))
            # Pipeline investment is counted from commitment until expected arrival.
            model.cost[q] += sum(day <= d < arrival for d in days)*case*term.cost/len(days)
    fees = {}
    for (day, sid), quantities in baskets.items():
        supplier = state.suppliers[sid]
        active = model.variable(high=1, integer=True)
        fees[active] = supplier.fee_cents
        coefficients = {q: orders[q][1].cost*orders[q][2] for q in quantities}
        coefficients[active] = -supplier.minimum_cents
        model.constraint(coefficients, low=0)
        for q in quantities:
            model.constraint({activation[q]: 1, active: -1}, high=0)
        model.constraint({active: 1, **{activation[q]: -1 for q in quantities}}, high=0)
        budgets[day-timedelta(days=day.weekday())][active] = supplier.fee_cents
    current_week = state.day-timedelta(days=state.day.weekday())
    for week, coefficients in budgets.items():
        model.constraint(coefficients, high=max(0, state.budget_cents-(state.week_spend if week == current_week else 0)))
    for lot in state.lots.values():
        if lot.units:
            lots.append(SupplyLot(lot.product, state.day, lot.expiry, lot.cost, fixed=lot.units))
    for incoming in state.incoming.values():
        if incoming.remaining and incoming.expected and incoming.expected > state.day:
            arrival = add_workdays(incoming.expected, settings.delay_workdays)
            lots.append(SupplyLot(incoming.product, arrival,
                                  arrival+timedelta(days=settings.incoming_freshness_days), incoming.cost,
                                  fixed=incoming.remaining))
    by_product = defaultdict(list)
    for line in demands:
        by_product[line.product].append(line)
    flows, on_time, line_flows = defaultdict(dict), {}, defaultdict(list)
    capacity = {day: {} for day in days}
    capacity_fixed = defaultdict(int)
    expiry_objective = {}
    for index, lot in enumerate(lots):
        previous = None
        for day in days:
            if day < lot.arrival or day >= lot.expiry:
                continue
            stock = model.variable(cost=lot.cost/len(days))
            balance = {stock: 1}
            if previous is not None:
                balance[previous] = -1
                capacity[day][previous] = state.products[lot.product].volume_ml
            elif lot.variable is not None:
                balance[lot.variable] = -lot.scale
                capacity[day][lot.variable] = lot.scale*state.products[lot.product].volume_ml
            else:
                capacity_fixed[day] += lot.fixed*state.products[lot.product].volume_ml
            for line in by_product[lot.product]:
                customer = state.customers[line.customer]
                if not (max(state.day, line.due) <= day <= add_workdays(line.due, customer.late_days)):
                    continue
                if lot.expiry < day+timedelta(days=customer.freshness_days) or day.weekday() >= 5:
                    continue
                # Continuous allocation is a planning relaxation; actual dispatch
                # always uses integer units and is checked in shared replay.
                flow = model.variable(high=line.remaining)
                balance[flow] = 1
                line_flows[line.id].append((day, flow))
                if day <= line.due:
                    on_time[flow] = 1
            right = lot.fixed if previous is None and lot.variable is None else 0
            model.constraint(balance, low=right, high=right)
            previous = stock
        if previous is not None and lot.expiry <= days[-1]+timedelta(days=1):
            expiry_objective[previous] = lot.cost
    for day in days:
        model.constraint(capacity[day], high=state.capacity_ml-capacity_fixed[day])
    for line in demands:
        entries = line_flows[line.id]
        model.constraint({f: 1 for _, f in entries}, high=line.remaining)
        # Recorded whole-line commitments are exact. Future forecast cohorts
        # are aggregate expectations, so their allocation is continuous here;
        # replay still applies the selected customer's whole-line rule.
        if (not line.estimated or bundle.pattern is not None) and not state.customers[line.customer].partial:
            activations = []
            for day in sorted({d for d, _ in entries}):
                active = model.variable(high=1, integer=True)
                activations.append(active)
                coefficients = {f: 1 for d, f in entries if d == day}
                coefficients[active] = -line.remaining
                model.constraint(coefficients, low=0, high=0)
            model.constraint({a: 1 for a in activations}, high=1)
    total = sum(d.remaining for d in demands)
    model.constraint(on_time, low=ceil(max(0, min(1, target_service))*total-1e-8))
    return model, orders, expiry_objective, fees


def solve_built(model: LinearModel, orders: dict, expiry_objective: dict,
                fees: dict, settings, started: float) -> tuple[list[Purchase], dict]:
    """Solve a constructed model and independently check case integrality."""
    result = model.solve(settings.solve_seconds * 0.8)
    primary = dict(status=int(result.status), message=result.message, variables=len(model.low),
                   constraints=len(model.lower), gap=float(result.mip_gap) if getattr(result, 'mip_gap', None) is not None else None)
    if result.x is None:
        return [], {**primary, 'available': False, 'elapsed_seconds': monotonic()-started}
    if result.status == 0:
        remaining = settings.solve_seconds - (monotonic()-started)
        if remaining > 0.1:
            optimum = float(np.dot(model.cost, result.x))
            model.constraint({i: c for i, c in enumerate(model.cost) if c}, high=optimum+0.01)
            secondary = np.zeros(len(model.low))
            for i, cost in expiry_objective.items():
                secondary[i] = cost
            # Lexicographic expiry before fees: fees have a known finite budget
            # bound and expire units are integer in physical replay.
            fee_bound = max(1, sum(fees.values())+1)
            for i, cost in fees.items():
                secondary[i] = cost/fee_bound
            refined = model.solve(remaining, secondary)
            if refined.x is not None:
                result = refined
            primary['secondary_status'] = int(refined.status)
    # Independent tolerances before interpreting any solver output as cases.
    x = result.x
    if any(abs(x[i]-round(x[i])) > 1e-5 for i, integer in enumerate(model.integer) if integer):
        return [], {**primary, 'available': False, 'reason': 'Nonintegral incumbent'}
    purchases = [Purchase(day, term.supplier, term.product, round(x[q])*case)
                 for q, (day, term, case) in orders.items() if round(x[q]) > 0]
    return purchases, {**primary, 'available': True, 'elapsed_seconds': monotonic()-started,
                       'model_investment_cents': float(np.dot(model.cost, x)),
                       'allocation_relaxation': 'Due-date/FEFO replay required; model flow is not a dispatch instruction'}


def solve_target(request: PlanRequest, bundle, target_service: float) -> tuple[list[Purchase], dict]:
    """Keep the single-view model available as the transparent comparison path."""
    started = monotonic()
    model, orders, expiry, fees = build_model(request, bundle, target_service)
    return solve_built(model, orders, expiry, fees, request.settings, started)


def order_keys(orders: dict) -> dict:
    """Identify decisions by business date and product, not internal column order."""
    return {(day, term.supplier, term.product): column
            for column, (day, term, case) in orders.items()}


def append_view(base: LinearModel, orders: dict, other: LinearModel, other_orders: dict) -> None:
    """Keep warehouses hypothetical but bind their purchasing decisions together."""
    offset, row_offset = len(base.low), len(base.lower)
    base.low.extend(other.low)
    base.high.extend(other.high)
    base.integer.extend(other.integer)
    # Optimise nominal stock exposure; other views are service/capacity safeguards.
    # No invented probability weights or lost-sale costs are introduced.
    base.cost.extend([0.0]*len(other.cost))
    base.rows.extend(row+row_offset for row in other.rows)
    base.columns.extend(column+offset for column in other.columns)
    base.values.extend(other.values)
    base.lower.extend(other.lower)
    base.upper.extend(other.upper)
    main_keys, other_keys = order_keys(orders), order_keys(other_orders)
    if main_keys.keys() != other_keys.keys():
        raise ValueError('Demand views must use identical purchasing opportunities')
    for key, column in main_keys.items():
        base.constraint({column: 1, other_keys[key]+offset: -1}, low=0, high=0)


def solve_joint(request: PlanRequest, bundles: dict, targets: dict) -> tuple[list[Purchase], dict]:
    """Choose one purchase schedule that meets every declared demand-view target.

    Views are stress cases, not observed future orders or probability estimates.
    Every view uses the same purchase quantities and supplier terms. Shared replay
    must still verify due-date, FEFO, whole-line and freshness outcomes.
    """
    if 'nominal' not in bundles or bundles.keys() != targets.keys():
        raise ValueError('Each demand view needs a target, including nominal')
    started = monotonic()
    bounds = defaultdict(int)
    for bundle in bundles.values():
        quantities = defaultdict(int)
        for demand in [d for d in request.snapshot.demand.values() if d.remaining]+projected_requests(request.snapshot, bundle):
            quantities[demand.product] += demand.remaining
        for product, quantity in quantities.items():
            bounds[product] = max(bounds[product], quantity)
    model, orders, expiry, fees = build_model(request, bundles['nominal'], targets['nominal'], bounds)
    for view in sorted(bundles):
        if view != 'nominal':
            additional, other_orders, _, _ = build_model(request, bundles[view], targets[view], bounds)
            append_view(model, orders, additional, other_orders)
    purchases, status = solve_built(model, orders, expiry, fees, request.settings, started)
    status.update(demand_views=sorted(bundles), service_targets=dict(targets),
                  objective_basis='Nominal stock investment; other views impose service and capacity constraints')
    return purchases, status
