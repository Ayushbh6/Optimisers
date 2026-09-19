"""Compare stock cover with bounded baskets judged by exact physical replay."""

from .baseline import order_today
from .contracts import Alternative, PlanRequest, PlanResult, Purchase
from .discrete import SearchBounds, optimise_basket
from .forecast import forecast
from .projection import planning_metrics, project
from .validation import validate_request


def baseline_schedule(request: PlanRequest, bundle) -> list[Purchase]:
    """Project future baseline ordering opportunities against the same demand view."""
    state, settings = request.snapshot, request.settings
    purchases = []
    def decide(current, shared_bundle):
        day = current.day
        if not any(s.weekday == day.weekday() for s in current.suppliers.values()):
            return []
        proposed = order_today(current, settings, bundle=bundle)
        if day == state.day:
            proposed = [p for p in proposed if p.product not in request.excluded and p.product not in request.locks]
            for product, units in request.locks.items():
                if units:
                    suppliers = [t.supplier for t in state.terms if t.product == product
                                 and state.suppliers[t.supplier].weekday == day.weekday()]
                    if len(suppliers) != 1:
                        raise ValueError(f'Locked product has no unambiguous supplier today: {product}')
                    proposed.append(Purchase(day, suppliers[0], product, units))
        purchases.extend(proposed)
        return proposed
    project(state, settings, [], bundle=bundle, policy=decide)
    return purchases


def plan(request: PlanRequest) -> PlanResult:
    """Return stock cover or a safer lower-investment exact-replay basket."""
    validate_request(request)
    state, settings = request.snapshot, request.settings
    bundle = forecast(state, settings)
    warnings = list(bundle.warnings)
    baseline = baseline_schedule(request, bundle)
    simulated = project(state, settings, baseline, bundle=bundle)
    baseline_metrics = planning_metrics(simulated, state, settings)
    alternatives = [Alternative('Stock-cover comparison', baseline, baseline_metrics, 'validated')]
    chosen, report = optimise_basket(request, bundle, baseline, SearchBounds())
    if chosen.name != 'Stock-cover comparison':
        alternatives.append(chosen)
    else:
        warnings.append('No validated lower-investment basket matches the comparison; retain the comparison')
    if any(row['rejection_reasons'] for row in report['candidate_outcomes']):
        warnings.append('Some baskets were rejected after exact demand-sensitivity checks; see the bounded search report')
    return PlanResult(request.identity(), alternatives, chosen.name, warnings, sensitivity={
        'basis': ('Today\'s candidate basket is replayed through exact warehouse dispatch under nominal, lower, '
                  'higher and four historical order-pattern views; future stock-cover decisions are recalculated '
                  'from each evolving replay state; no weighted business score'),
        'views': report['views'],
        'simulation_search': report,
    })
