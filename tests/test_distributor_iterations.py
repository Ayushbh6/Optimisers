"""Behaviour checks for diagnosed iteration defects; never require a savings win."""
from copy import deepcopy
from datetime import timedelta

from src.replenishment.baseline import order_today
from src.replenishment.contracts import Demand, ForecastBundle, PlannerSettings
from src.replenishment.forecast import projected_requests
from tests.test_replenishment import example


def test_baseline_same_purchases_with_preexpanded_forecast():
    state = example()
    state.capacity_ml = 100000
    state.demand['H'] = Demand('H', 'P', 'C', state.day-timedelta(days=10),
                               state.day-timedelta(days=9), 12, 12)
    settings = PlannerSettings()
    bundle = ForecastBundle('mean8', {('P', state.day+timedelta(days=i)): 1.7
                            for i in range(28) if (state.day+timedelta(days=i)).weekday()<5}, {}, [])
    before = order_today(state, settings, bundle=bundle)
    expanded = deepcopy(state)
    for d in projected_requests(state, bundle):
        expanded.demand[d.id] = d
    assert order_today(expanded, settings, bundle=bundle) == before


def test_cancelled_past_estimates_do_not_create_new_purchasing_need():
    state = example()
    state.demand['OLD-EST'] = Demand('OLD-EST', 'P', 'C', state.day-timedelta(days=5),
        state.day-timedelta(days=4), 100, cancelled=100, estimated=True)
    assert order_today(state, PlannerSettings(), bundle=ForecastBundle('mean8', {}, {}, [])) == []
