"""Hand examples that failed in archived v1 and must hold for every new revision."""
from copy import deepcopy
from datetime import timedelta
from tests.test_replenishment import example
from src.replenishment.baseline import order_today
from src.replenishment.contracts import Demand, ForecastBundle, Lot, PlannerSettings, Product, Term
from src.replenishment.forecast import projected_requests


def expanded(state,bundle):
    result=deepcopy(state)
    for row in projected_requests(state,bundle):
        result.demand[row.id]=row
    return result


def demand_view(state,rate):
    return ForecastBundle('mean8',{(p,state.day+timedelta(days=i)):rate
        for p in state.products for i in range(28) if (state.day+timedelta(days=i)).weekday()<5},{},[])


def history(state):
    for p in state.products:
        state.demand['H'+p]=Demand('H'+p,p,'C',state.day-timedelta(days=10),state.day-timedelta(days=9),12,12)


def test_fractional_forecast_is_not_generated_twice_in_nested_projection():
    state=example();state.capacity_ml=100000;history(state)
    bundle=demand_view(state,.7)
    direct=order_today(state,PlannerSettings(),bundle=bundle)
    nested=order_today(expanded(state,bundle),PlannerSettings(),bundle=bundle)
    assert [p.units for p in direct]==[6]
    assert nested==direct


def test_real_customer_commitment_keeps_priority_over_estimated_requests():
    state=example();state.capacity_ml=100000;state.budget_cents=1900
    state.products['Q']=Product('Q','Other',6,100,90)
    state.terms.append(Term('S','Q',100,6,state.day-timedelta(days=30)))
    history(state)
    state.lots['L']=Lot('L','P',state.day-timedelta(days=1),state.day+timedelta(days=90),100,6)
    state.demand['BOOKED']=Demand('BOOKED','P','C',state.day,state.day,12)
    bundle=demand_view(state,1.7)
    direct=order_today(state,PlannerSettings(),bundle=bundle)
    nested=order_today(expanded(state,bundle),PlannerSettings(),bundle=bundle)
    assert [(p.product,p.units) for p in direct]==[('P',18)]
    assert nested==direct
