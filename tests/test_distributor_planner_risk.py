"""A buyer must not receive a default that silently loses sensitivity coverage."""
from datetime import timedelta

from src.replenishment.contracts import ForecastBundle, PlannerSettings, PlanRequest, Purchase
from tests.test_replenishment import example


def load_planner(monkeypatch):
    from src.replenishment import planner
    return planner


def scenario(planner,monkeypatch,error):
    from src.replenishment.contracts import Demand
    state=example()
    state.request_history_start=state.day-timedelta(days=112)
    state.demand['H']=Demand('H','P','C',state.day-timedelta(days=7),state.day-timedelta(days=6),6,6)
    bundle=ForecastBundle('mean8',{('P',state.day+timedelta(days=2)):6},{'P':error},[])
    monkeypatch.setattr(planner,'forecast',lambda *args:bundle)
    monkeypatch.setattr(planner,'baseline_schedule',lambda *args:[Purchase(state.day,'S','P',12)])
    return planner.plan(PlanRequest(state,PlannerSettings()))


def test_nominally_sufficient_case_is_not_default_when_higher_demand_exposes_shortfall(monkeypatch):
    result=scenario(load_planner(monkeypatch),monkeypatch,5)
    assert result.recommended=='Stock-cover comparison'
    assert any('demand-sensitivity checks' in w for w in result.warnings)
    higher=result.sensitivity['views']['higher']
    assert higher['baseline']['on_time_units']==7
    smaller=[row for row in higher['alternatives'].values() if row['metrics']['investment_cents']<higher['baseline']['investment_cents']]
    assert smaller and max(row['metrics']['on_time_units'] for row in smaller)==6
    assert all(not row['accepted'] for row in smaller)


def test_identical_sensitivities_do_not_block_a_physically_sufficient_smaller_order(monkeypatch):
    result=scenario(load_planner(monkeypatch),monkeypatch,0)
    chosen=next(a for a in result.alternatives if a.name==result.recommended)
    assert chosen.purchases[0].units==6
