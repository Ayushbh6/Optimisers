"""Joint-view purchases cannot depend on which unknown future occurs."""
from src.replenishment import solver as module
from datetime import timedelta
import pytest
from tests.test_replenishment import example
from src.replenishment.contracts import Demand, ForecastBundle, PlanRequest, PlannerSettings
from src.replenishment.projection import project, planning_metrics


def setup():
    state=example()
    state.demand['H']=Demand('H','P','C',state.day-timedelta(days=7),state.day-timedelta(days=6),6,6)
    due=state.day+timedelta(days=2)
    bundles={view:ForecastBundle('mean8',{('P',due):units},{},[]) for view,units in [('nominal',6),('higher',7),('lower',2)]}
    return PlanRequest(state,PlannerSettings(solve_seconds=2)),bundles


def test_one_case_is_not_enough_when_same_purchases_must_cover_seven_units(monkeypatch):
    request,bundles=setup()
    purchases,status=module.solve_joint(request,bundles,{view:1.0 for view in bundles})
    assert status['available']
    assert sum(p.units for p in purchases)==12
    for bundle in bundles.values():
        projection=project(request.snapshot,request.settings,purchases,bundle=bundle)
        assert planning_metrics(projection,request.snapshot,request.settings)['service']==1.0
        assert projection.audit()==[]


def test_known_budget_can_make_joint_service_impossible(monkeypatch):
    request,bundles=setup();request.snapshot.budget_cents=700
    purchases,status=module.solve_joint(request,bundles,{view:1.0 for view in bundles})
    assert not status['available']
    assert purchases==[]


def test_views_require_explicit_targets(monkeypatch):
    request,bundles=setup()
    with pytest.raises(ValueError,match='Each demand view'):
        module.solve_joint(request,bundles,{'nominal':1.0})


def test_equal_total_demand_does_not_imply_equal_whole_line_service():
    from src.replenishment.contracts import Customer,Lot
    from src.replenishment.physical import Operations
    totals=[]
    for quantities in ([6,6,6,6],[24]):
        state=example();state.customers['C']=Customer('C',False,0,14)
        state.lots['L']=Lot('L','P',state.day,state.day+timedelta(days=60),100,12)
        for i,quantity in enumerate(quantities):
            due=state.day+timedelta(days=i)
            state.demand[str(i)]=Demand(str(i),'P','C',state.day,due,quantity,estimated=True)
        op=Operations(state)
        for i in range(4):
            if i:op.begin_day(state.day+timedelta(days=i))
            op.finish_day()
        assert op.audit()==[]
        totals.append(sum(d.on_time for d in op.state.demand.values()))
    assert totals==[12,0]


def test_historical_whole_line_cannot_be_partially_allocated_to_meet_target():
    from src.replenishment.contracts import Customer, Lot
    state=example();state.customers['C']=Customer('C',False,0,14)
    state.lots['L']=Lot('L','P',state.day,state.day+timedelta(days=60),100,12)
    line=Demand('PAT','P','C',state.day,state.day,24,estimated=True)
    bundle=ForecastBundle('mean8',{('P',state.day):24},{},[],pattern=[line])
    purchases,status=module.solve_target(PlanRequest(state,PlannerSettings(horizon_days=7)),bundle,0.5)
    assert not status['available']
    assert purchases==[]
