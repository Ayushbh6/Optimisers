"""Malformed operational records fail clearly without silently changing them."""
from datetime import timedelta
from dataclasses import replace

import pytest
from tests.test_replenishment import example
from src.replenishment.contracts import Incoming, Demand, PlanRequest, PlannerSettings, Lot

from src.replenishment import validation


def incoming(state):
    return Incoming('I','PO','S','P',state.day,state.day+timedelta(days=2),6,100)


def test_unknown_supplier_and_product_are_explicit_errors():
    state=example();line=incoming(state);line.supplier='UNKNOWN';line.product='UNKNOWN'
    state.incoming[line.id]=line
    assert any('unknown supplier/product' in e for e in validation.validate_state(state))


@pytest.mark.parametrize('bad', [None,'6',6.5,True,-1])
def test_malformed_incoming_units_do_not_raise_arithmetic_errors(bad):
    state=example();line=incoming(state);line.units=bad;state.incoming[line.id]=line
    assert any('units: integer' in e for e in validation.validate_state(state))


def test_invalid_date_gives_a_record_error_not_python_comparison_error():
    state=example();line=incoming(state);line.placed='yesterday';state.incoming[line.id]=line
    assert any('purchase date: calendar date' in e for e in validation.validate_state(state))


def test_unreliable_eta_can_remain_unknown():
    state=example();line=incoming(state);line.expected=None;state.incoming[line.id]=line
    assert validation.validate_state(state)==[]


def test_duplicate_effective_terms_are_rejected():
    state=example();state.terms.append(state.terms[0])
    assert any('overlapping commercial terms' in e for e in validation.validate_state(state))


def test_past_eta_is_visible_but_not_treated_as_invalid_history():
    state=example();line=incoming(state);line.placed-=timedelta(days=7);line.expected=state.day-timedelta(days=2)
    state.incoming[line.id]=line
    assert validation.validate_state(state)==[]


def test_known_overcapacity_is_not_silently_ignored():
    state=example();state.lots['L']=Lot('L','P',state.day,state.day+timedelta(days=60),100,13)
    assert 'Opening stock exceeds declared storage capacity' in validation.validate_state(state)


def test_future_request_cannot_bypass_boundary_using_estimated_label():
    state=example();day=state.day+timedelta(days=1)
    state.demand['F']=Demand('F','P','C',day,day,6,estimated=True)
    assert any('future request' in e for e in validation.validate_state(state))


@pytest.mark.parametrize('field,value', [('horizon_days',True),('solve_seconds',float('inf')),
    ('demand_multiplier',float('nan')),('incoming_freshness_days','60'),('delay_workdays',1.5)])
def test_invalid_planning_assumptions_are_rejected(field,value):
    request=PlanRequest(example(),replace(PlannerSettings(),**{field:value}))
    with pytest.raises(ValueError,match=field):validation.validate_request(request)


def test_unknown_excluded_product_is_not_silently_discarded():
    with pytest.raises(ValueError,match='Unknown excluded product'):
        validation.validate_request(PlanRequest(example(),excluded=('MISSING',)))
