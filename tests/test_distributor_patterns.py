"""Historical patterns preserve real request structure without revealing future events."""
from copy import deepcopy
from datetime import timedelta
from tests.test_replenishment import example
from src.replenishment.contracts import Demand,ForecastBundle
from src.replenishment.patterns import historical_patterns,pattern_remainder


def fixture():
    state=example();state.request_history_start=state.day-timedelta(days=112)
    state.demand['H']=Demand('H','P','C',state.day-timedelta(days=25),state.day-timedelta(days=21),24,shipped=12,cancelled=12)
    return state,ForecastBundle('mean8',{}, {}, [])


def test_pattern_retains_whole_request_size_customer_and_weekday():
    state,bundle=fixture();before=state.identity()
    views=historical_patterns(state,bundle)
    row=views['history-1'].pattern[0]
    assert (row.units,row.customer,row.due.weekday())==(24,'C',state.demand['H'].due.weekday())
    assert row.estimated and row.shipped==row.cancelled==row.on_time==0
    assert state.identity()==before
    assert views['history-2'].pattern==[]


def test_unavailable_history_does_not_become_zero_demand():
    state,bundle=fixture();state.request_history_start=None
    assert historical_patterns(state,bundle)=={}
    state.request_history_start=state.day-timedelta(days=28)
    assert list(historical_patterns(state,bundle))==['history-1']


def test_future_mutation_cannot_change_historical_patterns():
    state,bundle=fixture();before=historical_patterns(state,bundle)
    state.demand['F']=Demand('F','P','C',state.day+timedelta(days=1),state.day+timedelta(days=2),9999)
    assert historical_patterns(state,bundle)==before


def test_bookings_replace_pattern_units_instead_of_being_added_twice():
    state,bundle=fixture();pattern=historical_patterns(state,bundle)['history-1'].pattern
    due=pattern[0].due;state.demand['B']=Demand('B','P','C',state.day,due,10)
    assert sum(d.units for d in pattern_remainder(state,pattern))==14
    state.demand['B'].units=30
    assert pattern_remainder(state,pattern)==[]
    assert pattern[0].units==24


def test_historical_prior_bookings_are_not_invented_as_future_requests():
    state,bundle=fixture()
    state.demand['PRIOR']=Demand('PRIOR','P','C',state.day-timedelta(days=29),
                                state.day-timedelta(days=27),99,shipped=99)
    pattern=historical_patterns(state,bundle)['history-1'].pattern
    assert [row.units for row in pattern]==[24]
