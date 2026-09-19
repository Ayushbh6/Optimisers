"""Hand-calculated checks for bounded exact-warehouse basket selection."""
from datetime import timedelta

from src.replenishment.contracts import Demand, ForecastBundle, Lot, PlanRequest, PlannerSettings, Product, Purchase, Term
from src.replenishment.discrete import SearchBounds, generate_baskets, optimise_basket
from src.replenishment.projection import planning_metrics, project
from tests.test_replenishment import example


def two_product_state(*, supplier_minimum: int = 0):
    state = example()
    state.capacity_ml = 100_000
    state.suppliers['S'] = type(state.suppliers['S'])('S', state.day.weekday(), 2, supplier_minimum, 100)
    state.products['Q'] = Product('Q', 'Soup', 6, 100, 90)
    state.terms.append(Term('S', 'Q', 100, 6, state.day-timedelta(days=30)))
    return state


def seven_empty_views(bundle):
    return {name: bundle for name in ('nominal', 'lower', 'higher', 'history-1', 'history-2', 'history-3', 'history-4')}


def test_candidate_generation_repairs_supplier_basket_with_needed_product():
    state = two_product_state(supplier_minimum=1200)
    baseline = [Purchase(state.day, 'S', 'P', 12), Purchase(state.day, 'S', 'Q', 6)]
    rows, report = generate_baskets(PlanRequest(state), baseline,
                                    SearchBounds(max_candidates=20, max_two_line_candidates=4))
    replacement = next(row for row in rows if row['reason'] == 'remove P')
    assert replacement['purchases'] == [Purchase(state.day, 'S', 'Q', 12)]
    assert report['baseline_lines'] == 2
    assert report['feasible_candidates'] <= 20
    assert any(row['reason'].startswith('two-line:') for row in rows)


def test_search_bounds_are_explicit_and_deterministic():
    state = two_product_state()
    baseline = [Purchase(state.day, 'S', 'P', 12), Purchase(state.day, 'S', 'Q', 12)]
    bounds = SearchBounds(max_lines=1, case_steps=1, max_two_line_candidates=1, max_candidates=2)
    first, first_report = generate_baskets(PlanRequest(state), baseline, bounds)
    second, second_report = generate_baskets(PlanRequest(state), baseline, bounds)
    assert first == second
    assert first_report == second_report
    assert len(first) == 2
    assert first_report['omitted_lines'] == 1


def test_selected_prediction_is_the_exact_physical_replay():
    state = two_product_state()
    state.lots['OPEN-P'] = Lot('OPEN-P', 'P', state.day, state.day+timedelta(days=90), 100, 6)
    state.demand['BOOKED-P'] = Demand('BOOKED-P', 'P', 'C', state.day, state.day, 6)
    settings = PlannerSettings(horizon_days=7, forecast_method='mean8')
    request = PlanRequest(state, settings)
    baseline = [Purchase(state.day, 'S', 'P', 6), Purchase(state.day, 'S', 'Q', 6)]
    bundle = ForecastBundle('mean8', {}, {'P': 0, 'Q': 0}, [])
    selected, report = optimise_basket(
        request, bundle, baseline,
        SearchBounds(max_candidates=20, max_two_line_candidates=4),
        views=seven_empty_views(bundle),
    )
    assert selected.name == 'Simulation-checked basket'
    assert report['selected_candidate']['changes'] == [{
        'supplier': 'S', 'product': 'Q', 'baseline_units': 6,
        'candidate_units': 0, 'change_units': -6, 'case_size': 6,
        'reason': 'remove Q',
    }]
    replay = project(state, settings, selected.purchases, bundle=bundle)
    exact = planning_metrics(replay, state, settings)
    assert selected.metrics == exact == report['selected_candidate']['checks']['nominal']['candidate']
    assert exact['booked_fulfilled_units'] == 6
    assert report['selected_cash_required_cents'] == 700
    assert report['replay_count'] == 7 * (1 + report['generation']['feasible_candidates'])
    assert report['future_policy'].startswith('adaptive stock cover')
    assert report['elapsed_seconds'] >= 0


def test_adaptive_future_basket_rejects_cross_product_budget_displacement():
    """Six deferred units can crowd another product out of next week's basket."""
    state = two_product_state()
    state.budget_cents = 1400
    state.terms = [
        Term('S', 'P', 100, 6, state.day-timedelta(days=30)),
        Term('S', 'Q', 200, 6, state.day-timedelta(days=30)),
    ]
    settings = PlannerSettings(horizon_days=14, forecast_method='mean8')
    pattern = [
        Demand('EST-P-NOW', 'P', 'C', state.day, state.day+timedelta(days=2), 6, estimated=True),
        Demand('EST-P-NEXT', 'P', 'C', state.day, state.day+timedelta(days=9), 6, estimated=True),
        Demand('EST-Q-NEXT', 'Q', 'C', state.day, state.day+timedelta(days=9), 6, estimated=True),
    ]
    bundle = ForecastBundle('mean8', {}, {'P': 0, 'Q': 0}, [], pattern=pattern)
    baseline = [Purchase(state.day, 'S', 'P', 12)]
    selected, report = optimise_basket(
        PlanRequest(state, settings), bundle, baseline,
        SearchBounds(max_candidates=8, max_two_line_candidates=2),
        views=seven_empty_views(bundle),
    )
    reduced = next(row for row in report['candidate_outcomes']
                   if row['generation_reason'] == 'reduce P by 1 case(s)')
    nominal = reduced['checks']['nominal']
    assert selected.name == 'Stock-cover comparison'
    assert not reduced['accepted']
    assert nominal['on_time_change'] == -6
    assert nominal['delivery_losses'] == [{
        'line': 'EST-Q-NEXT', 'customer': 'C', 'product': 'Q', 'estimated': True,
        'on_time_change': -6, 'shipped_change': -6,
    }]
    assert 'nominal: line-level delivery loss' in reduced['rejection_reasons']
    # Baseline buys Q next week. The reduced path first replaces P, leaving too
    # little allowance for Q's 6-unit minimum and its €12.00 line cost.
    assert nominal['baseline_purchase_lines'] == 2
    assert nominal['candidate_purchase_lines'] == 2


def test_selected_adaptive_schedule_exactly_matches_fixed_physical_replay():
    state = example()
    state.capacity_ml = 100_000
    settings = PlannerSettings(horizon_days=14, forecast_method='mean8')
    pattern = [
        Demand('EST-P-NOW', 'P', 'C', state.day, state.day+timedelta(days=2), 6, estimated=True),
        Demand('EST-P-NEXT', 'P', 'C', state.day, state.day+timedelta(days=9), 6, estimated=True),
    ]
    bundle = ForecastBundle('mean8', {}, {'P': 0}, [], pattern=pattern)
    selected, report = optimise_basket(
        PlanRequest(state, settings), bundle, [Purchase(state.day, 'S', 'P', 12)],
        SearchBounds(max_candidates=8, max_two_line_candidates=2),
        views=seven_empty_views(bundle),
    )
    assert selected.name == 'Simulation-checked basket'
    assert [(row.day-state.day, row.units) for row in selected.purchases] == [
        (timedelta(0), 6), (timedelta(days=7), 6),
    ]
    exact = planning_metrics(project(state, settings, selected.purchases, bundle=bundle), state, settings)
    assert selected.metrics == exact == report['selected_candidate']['checks']['nominal']['candidate']
    assert exact['on_time_units'] == 12
