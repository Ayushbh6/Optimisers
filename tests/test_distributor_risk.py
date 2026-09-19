"""Independent boundary checks for the proposed sensitivity view."""
from datetime import date, timedelta

import pytest
from src.replenishment.contracts import ForecastBundle

from src.replenishment import risk


def test_one_week_error_is_spread_over_five_weekdays_without_mutation():
    monday=date(2025,7,7)
    daily={('P',monday+timedelta(days=i)): 2.0 if i<5 else 0.0 for i in range(7)}
    bundle=ForecastBundle('mean8',daily,{'P':5.0},[])
    views=risk.demand_sensitivities(bundle)
    assert sum(views['nominal'].daily.values())==10
    assert sum(views['higher'].daily.values())==15
    assert sum(views['lower'].daily.values())==5
    assert bundle.daily==daily and bundle.warnings==[]
    assert views['higher'].daily['P',monday+timedelta(days=6)]==0


def test_lower_view_cannot_create_negative_customer_demand():
    day=date(2025,7,7)
    bundle=ForecastBundle('mean8',{('P',day):1.0},{'P':20.0},[])
    assert risk.demand_sensitivities(bundle)['lower'].daily['P',day]==0


@pytest.mark.parametrize('invalid', [-1.0,float('nan'),float('inf')])
def test_invalid_observed_errors_are_rejected(invalid):
    with pytest.raises(ValueError,match='weekly error'):
        risk.demand_sensitivities(ForecastBundle('mean8',{}, {'P':invalid}, []))


def test_same_schedule_has_identical_results_in_each_sensitivity():
    from tests.test_replenishment import example
    from src.replenishment.contracts import Demand, PlannerSettings, Purchase
    state=example()
    state.demand['H']=Demand('H','P','C',state.day-timedelta(days=7),state.day-timedelta(days=6),10,10)
    bundle=ForecastBundle('mean8',{('P',state.day+timedelta(days=2)):6},{'P':5},[])
    schedule=[Purchase(state.day,'S','P',6)]
    original=state.identity()
    views=risk.compare_sensitivities(state,PlannerSettings(),schedule,{'same':schedule},bundle)
    for view in views.values():
        same=view['alternatives']['same']
        assert same['metrics']==view['baseline']
        assert same['preserves_service'] and same['preserves_booked']
    assert state.identity()==original


def test_sensitivity_does_not_reduce_or_duplicate_real_bookings():
    from tests.test_replenishment import example
    from src.replenishment.contracts import Demand
    from src.replenishment.forecast import projected_requests
    state=example()
    state.demand['H']=Demand('H','P','C',state.day-timedelta(days=7),state.day-timedelta(days=6),10,10)
    state.demand['BOOKED']=Demand('BOOKED','P','C',state.day,state.day,12)
    bundle=ForecastBundle('mean8',{('P',state.day):10},{'P':20},[])
    views=risk.demand_sensitivities(bundle)
    assert sum(d.units for d in projected_requests(state,views['lower']))==0
    assert sum(d.units for d in projected_requests(state,views['higher']))==2
    assert state.demand['BOOKED'].units==12
