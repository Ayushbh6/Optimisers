"""Independent hand examples for the shared operational and forecasting contract."""
from datetime import date, timedelta
from copy import deepcopy

import pytest

from src.replenishment.contracts import Customer, Demand, Incoming, Lot, PlanningSnapshot, Product, Purchase, Supplier, Term, PlannerSettings
from src.replenishment.physical import Operations, validate_purchases
from src.replenishment.forecast import ForecastBundle, projected_requests, daily_estimates
from src.replenishment.projection import project


def example():
    day = date(2025, 7, 7)
    return PlanningSnapshot(day, {'P': Product('P', 'Pasta', 6, 100, 90)},
        {'S': Supplier('S', 0, 2, 0, 100)}, {'C': Customer('C', True, 2, 14)},
        [Term('S', 'P', 100, 6, date(2025, 1, 1))], {}, {}, {}, 5000, 1200)


def test_hand_sequence_partial_capacity_expiry_and_cancel():
    state = example()
    state.day -= timedelta(days=1)
    op = Operations(state)
    monday = date(2025, 7, 7)
    op.begin_day(monday)
    op.add_demand(Demand('D', 'P', 'C', monday, monday+timedelta(days=2), 15))
    incoming = op.place([Purchase(monday, 'S', 'P', 18)])[0]
    op.finish_day()
    op.begin_day(monday+timedelta(days=1)); op.finish_day()
    op.begin_day(monday+timedelta(days=2))
    assert op.receive(incoming.id, 18, monday+timedelta(days=30)) == 6
    op.finish_day()
    assert op.state.demand['D'].on_time == 12
    op.begin_day(monday+timedelta(days=3))
    assert op.receive(incoming.id, 6, monday+timedelta(days=30)) == 0
    op.finish_day()
    assert op.state.demand['D'].shipped == 15
    assert sum(l.units for l in op.state.lots.values()) == 3
    op.begin_day(monday+timedelta(days=30)); op.finish_day()
    assert sum(l.units for l in op.state.lots.values()) == 0
    assert op.audit() == []
    assert sum(-m['quantity'] for m in op.movements if m['kind']=='expiry') == 3


def test_whole_line_and_freshness_are_not_relaxed():
    state = example()
    state.customers['C'] = Customer('C', False, 0, 30)
    state.lots['A'] = Lot('A', 'P', state.day, state.day+timedelta(days=29), 100, 6)
    state.lots['B'] = Lot('B', 'P', state.day, state.day+timedelta(days=60), 100, 6)
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, 10)
    op = Operations(state); op.finish_day()
    assert op.state.demand['D'].shipped == 0
    assert op.state.demand['D'].cancelled == 10
    assert op.audit() == []


def test_purchase_cases_fees_budget_and_order_day():
    state = example()
    assert validate_purchases(state, [Purchase(state.day, 'S', 'P', 7)])
    state.budget_cents = 699
    assert validate_purchases(state, [Purchase(state.day, 'S', 'P', 6)])
    state.budget_cents = 700
    assert not validate_purchases(state, [Purchase(state.day, 'S', 'P', 6)])
    state.suppliers['S'] = Supplier('S', 1, 2, 0, 100)
    assert validate_purchases(state, [Purchase(state.day, 'S', 'P', 6)])


def test_bookings_are_not_added_to_forecast():
    state = example()
    state.demand['H'] = Demand('H', 'P', 'C', state.day-timedelta(days=5), state.day-timedelta(days=4), 10, 10)
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, 7)
    bundle = ForecastBundle('mean4', {('P', state.day): 10}, {}, [])
    estimated = projected_requests(state, bundle)
    assert sum(d.units for d in estimated) == 3
    assert all(d.estimated for d in estimated)
    bundle.daily['P', state.day] = 5
    assert projected_requests(state, bundle) == []


def test_future_record_does_not_change_earlier_forecast():
    state = example()
    before = daily_estimates(state, state.day, [state.day], 'mean4')
    state.demand['FUTURE'] = Demand('FUTURE', 'P', 'C', state.day+timedelta(days=2), state.day+timedelta(days=3), 10000)
    assert daily_estimates(state, state.day, [state.day], 'mean4') == before


def test_projection_no_order_and_no_mutation():
    state = example()
    state.lots['A'] = Lot('A', 'P', state.day, state.day+timedelta(days=90), 100, 12)
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, 6)
    identity = state.identity()
    result = project(state, PlannerSettings(), [], bundle=ForecastBundle('mean4', {}, {}, []))
    assert result.state.demand['D'].on_time == 6
    assert state.identity() == identity
    assert result.audit() == []


def test_solver_small_case_is_independently_replayed():
    from src.replenishment.contracts import PlanRequest
    from src.replenishment.solver import solve_target
    state = example()
    state.capacity_ml = 10000
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day+timedelta(days=2), 5)
    bundle = ForecastBundle('mean4', {}, {}, [])
    purchases, status = solve_target(PlanRequest(state, PlannerSettings(horizon_days=7)), bundle, 1.0)
    assert status['available']
    assert purchases == [Purchase(state.day, 'S', 'P', 6)]
    replay = project(state, PlannerSettings(horizon_days=7), purchases, bundle=bundle)
    assert replay.state.demand['D'].on_time == 5
    assert sum(l.units for l in replay.state.lots.values()) == 1


def test_solver_cannot_rescue_order_due_before_receipt():
    from src.replenishment.contracts import PlanRequest
    from src.replenishment.solver import solve_target
    state = example()
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, 5)
    purchases, status = solve_target(PlanRequest(state, PlannerSettings(horizon_days=7)),
                                    ForecastBundle('mean4', {}, {}, []), 1.0)
    assert not status['available']
    assert status['status'] == 2


def test_cloning_operational_state_keeps_new_ids_unique():
    state = example()
    op = Operations(state)
    incoming = op.place([Purchase(state.day, 'S', 'P', 6)])[0]
    op.begin_day(state.day+timedelta(days=2))
    op.receive(incoming.id, 3, state.day+timedelta(days=60))
    clone = Operations(op.state)
    clone.receive(incoming.id, 3, state.day+timedelta(days=60))
    assert len(clone.state.lots) == 2
    assert clone.audit() == []


def test_journal_corruption_is_detected():
    state = example()
    state.lots['A'] = Lot('A', 'P', state.day, state.day+timedelta(days=60), 100, 6)
    op = Operations(state)
    op.state.lots['A'].units -= 1
    assert op.audit() == ['Lot balance mismatch: A']


def test_planning_modules_do_not_import_evaluator_or_generator():
    import ast
    from pathlib import Path
    for name in ('planner', 'solver', 'forecast', 'baseline', 'physical', 'projection', 'contracts', 'state'):
        tree = ast.parse(Path(f'src/replenishment/{name}.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(word in (node.module or '') for word in ('evaluator', 'external', 'generator', 'catalog'))


def test_fefo_uses_oldest_eligible_lot_and_stable_customer_priority():
    state = example()
    state.lots['NEW'] = Lot('NEW', 'P', state.day, state.day+timedelta(days=60), 100, 6)
    state.lots['OLD'] = Lot('OLD', 'P', state.day, state.day+timedelta(days=20), 100, 6)
    state.demand['B'] = Demand('B', 'P', 'C', state.day, state.day, 8)
    state.demand['A'] = Demand('A', 'P', 'C', state.day, state.day, 8)
    op = Operations(state); op.finish_day()
    assert op.deliveries[0] == dict(day=str(state.day), line='A', lot='OLD', units=6)
    assert op.state.demand['A'].shipped == 8
    assert op.state.demand['B'].shipped == 4


def test_unscheduled_overdue_incoming_does_not_protect_order():
    state = example()
    state.incoming['I'] = Incoming('I', 'O', 'S', 'P', state.day-timedelta(days=7), state.day, 12, 100)
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, 6)
    result = project(state, PlannerSettings(horizon_days=4), [], bundle=ForecastBundle('mean4', {}, {}, []))
    assert result.state.demand['D'].shipped == 0
    assert result.state.incoming['I'].remaining == 12
    assert result.audit() == []


def test_partial_receipt_never_erases_supplier_balance():
    state = example()
    state.capacity_ml = 500
    state.incoming['I'] = Incoming('I', 'O', 'S', 'P', state.day-timedelta(days=7), state.day, 12, 100)
    op = Operations(state)
    assert op.receive('I', 12, state.day+timedelta(days=60)) == 7
    assert op.state.incoming['I'].remaining == 7
    assert op.audit() == []


def test_weekly_budget_resets_without_erasing_pipeline():
    state = example()
    state.week_spend = 4900
    state.incoming['I'] = Incoming('I', 'O', 'S', 'P', state.day, state.day+timedelta(days=9), 12, 100)
    op = Operations(state)
    op.begin_day(state.day+timedelta(days=7))
    assert op.state.week_spend == 0
    assert op.state.incoming['I'].remaining*op.state.incoming['I'].cost == 1200


def test_forecast_uses_unfulfilled_requests_and_preserves_fractional_volume():
    state = example()
    state.demand['H'] = Demand('H', 'P', 'C', state.day-timedelta(days=10), state.day-timedelta(days=7), 10, 0, 10)
    estimates = daily_estimates(state, state.day, [state.day], 'mean4')
    assert estimates['P', state.day] == .5
    bundle = ForecastBundle('mean4', {('P', state.day+timedelta(days=i)): .5 for i in range(4)}, {}, [])
    assert sum(d.units for d in projected_requests(state, bundle)) == 2


def test_milp_budget_and_supplier_minimum_infeasibility():
    from src.replenishment.contracts import PlanRequest
    from src.replenishment.solver import solve_target
    state = example()
    state.suppliers['S'] = Supplier('S', 0, 2, 1200, 100)
    state.budget_cents = 1200
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day+timedelta(days=2), 5)
    p, status = solve_target(PlanRequest(state, PlannerSettings(horizon_days=7)), ForecastBundle('mean4', {}, {}, []), 1)
    assert not status['available']
    state.budget_cents = 1300
    p, status = solve_target(PlanRequest(state, PlannerSettings(horizon_days=7)), ForecastBundle('mean4', {}, {}, []), 1)
    assert status['available'] and p[0].units == 12


def test_evaluation_seed_guard_fails_before_creating_files(tmp_path):
    from src.demo_data.config import default_config
    from src.replenishment.scenarios import materialise
    with pytest.raises(ValueError, match='frozen evaluation contract'):
        materialise(default_config('ordinary', 4404), tmp_path/'must-not-exist')
    assert not (tmp_path/'must-not-exist').exists()


def test_forecast_selection_includes_last_completed_history_week():
    from src.replenishment.forecast import historical_scores
    state = example()
    state.day = date(2025, 7, 6)  # End of Sunday: the preceding week is complete.
    state.demand['LAST'] = Demand('LAST', 'P', 'C', date(2025, 7, 2), date(2025, 7, 4), 20)
    scores = historical_scores(state)
    # No earlier requests exist, so the final week's unanticipated 20 units
    # must contribute exactly 20 units to the eight-week backtest error.
    assert scores['mean8']['absolute_unit_error'] == 20


def test_request_identity_covers_assumptions_and_edits():
    from src.replenishment.contracts import PlanRequest
    a = PlanRequest(example())
    b = PlanRequest(example(), PlannerSettings(demand_multiplier=1.2))
    assert a.identity() != b.identity()
    b = PlanRequest(example(), locks={'P': 6})
    assert a.identity() != b.identity()


def test_missing_cost_and_invalid_quantities_raise_clear_errors():
    from src.replenishment.contracts import PlanRequest
    from src.replenishment.validation import validate_request
    state = example()
    state.terms[0] = Term('S', 'P', None, 6, date(2025, 1, 1))
    with pytest.raises(ValueError, match='purchase cost cents'):
        validate_request(PlanRequest(state))
    state = example()
    state.demand['D'] = Demand('D', 'P', 'C', state.day, state.day, None)
    with pytest.raises(ValueError, match='integer'):
        validate_request(PlanRequest(state))


def test_reduced_allowance_does_not_make_no_order_invalid():
    state = example()
    state.week_spend = 700
    state.budget_cents = 500
    assert validate_purchases(state, []) == []
    assert validate_purchases(state, [Purchase(state.day, 'S', 'P', 6)])


def test_duplicate_supplier_commitment_and_money_corruption_are_detected():
    state = example()
    op = Operations(state)
    op.place([Purchase(state.day, 'S', 'P', 6)])
    with pytest.raises(ValueError, match='already been committed'):
        op.place([Purchase(state.day, 'S', 'P', 6)])
    assert op.audit() == []
    op.state.week_spend -= 1
    assert 'Purchasing spend accumulator does not reconcile' in op.audit()


def test_supplier_notices_release_only_when_known_and_partial_balance_survives(tmp_path):
    from src.demo_data.schema import EVALUATOR_SCHEMA, create_database
    from src.replenishment.evaluator import World
    db = create_database(tmp_path/'evaluator.sqlite', EVALUATOR_SCHEMA)
    db.execute('INSERT INTO future_supplier_conditions VALUES (?,?,?,?,?,?,?)',
               ('X', 'S', '2025-07-09', '2025-07-09', 1, 5000, '2025-07-09'))
    db.commit(); db.close()
    state = example()
    op = Operations(state)
    incoming = op.place([Purchase(state.day, 'S', 'P', 6)])[0]
    world = World(tmp_path)
    identity = op.state.identity()
    world.schedule(op, incoming)
    assert op.state.identity() == identity  # Scheduling hidden events exposes nothing.
    op.finish_day()
    op.begin_day(date(2025, 7, 8)); world.release(op); op.finish_day()
    assert op.state.notices == []
    op.begin_day(date(2025, 7, 9)); world.release(op); op.finish_day()
    assert incoming.expected == date(2025, 7, 10)
    assert incoming.received == 0
    op.begin_day(date(2025, 7, 10)); world.release(op); op.finish_day()
    assert incoming.received == 3 and incoming.remaining == 3
    assert incoming.expected == date(2025, 7, 14)
    for day in (date(2025, 7, 11), date(2025, 7, 12), date(2025, 7, 13), date(2025, 7, 14)):
        op.begin_day(day)
        if day.weekday() < 5:
            world.release(op)
        op.finish_day()
    assert incoming.remaining == 0
    assert op.audit() == []


def test_supplier_conditions_do_not_depend_on_policy_order_identifiers(tmp_path):
    from src.demo_data.schema import EVALUATOR_SCHEMA, create_database
    from src.replenishment.evaluator import World
    db = create_database(tmp_path/'evaluator.sqlite', EVALUATOR_SCHEMA)
    db.execute('INSERT INTO future_supplier_conditions VALUES (?,?,?,?,?,?,?)',
               ('X', 'S', '2025-07-09', '2025-07-09', 1, 5000, '2025-07-09'))
    db.commit(); db.close()
    a, b = World(tmp_path), World(tmp_path)
    op = Operations(example())
    one = Incoming('A', 'PO-A', 'S', 'P', op.state.day, date(2025, 7, 9), 12, 100)
    other = Incoming('UNRELATED-ID', 'PO-B', 'S', 'P', op.state.day, date(2025, 7, 9), 12, 100)
    a.schedule(op, one)
    b.schedule(op, other)
    def quantities(world):
        return [(r['day'], r['units'], r['expiry']) for r in world.pending]
    assert quantities(a) == quantities(b)


def test_evaluator_materialisation_matches_retained_v2_recipe(tmp_path, monkeypatch):
    from pathlib import Path
    import sqlite3
    from src.demo_data.config import default_config
    from src.demo_data.generator import generate_scenario
    import src.demo_data.storage as storage
    from src.replenishment.scenarios import materialise
    # Both materialisers use the exact original history engine and future recipe.
    # Override only the output-root validator for pytest's repo-local fixture.
    monkeypatch.setattr('src.replenishment.scenarios.validate_output', lambda p: p)
    monkeypatch.setattr('src.demo_data.generator.validate_output', lambda p: p)
    a, b = tmp_path/'original', tmp_path/'evaluation'
    generate_scenario(default_config(), a)
    materialise(default_config(), b)
    for filename in ('operational.sqlite', 'evaluator.sqlite'):
        with sqlite3.connect(a/filename) as first, sqlite3.connect(b/filename) as second:
            assert list(first.iterdump()) == list(second.iterdump())
