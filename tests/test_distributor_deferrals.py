"""Hand examples for exact-dispatch deferral review, not savings targets."""
from datetime import timedelta
from pathlib import Path
import shutil
import pytest
from tests.test_replenishment import example
from src.replenishment.contracts import Purchase,PlannerSettings,ForecastBundle,Demand,Lot,Customer
from src.replenishment.projection import project
from src.distributor_research.deferrals import defer_line,compare_dispatch


@pytest.fixture(scope="module")
def operational_path():
    """Rebuild the removed historical demo database instead of requiring retained bulk data."""
    from src.demo_data.config import default_config
    from src.demo_data.generator import generate_scenario
    work = Path("artifacts/distributor-demo/.test-work-deferrals")
    shutil.rmtree(work, ignore_errors=True)
    scenario = work / "scenario"
    generate_scenario(default_config("supplier_disruption", 2202), scenario)
    yield scenario / "operational.sqlite"
    shutil.rmtree(work, ignore_errors=True)


def test_deferral_preserves_units_and_merges_existing_next_week_line():
    s=example();p=Purchase(s.day,'S','P',6);q=Purchase(s.day+timedelta(days=7),'S','P',12)
    assert defer_line([p,q],p)==[Purchase(q.day,'S','P',18)]


def test_stock_covers_delivery_and_deferral_reduces_stock_days_exactly():
    s=example();s.capacity_ml=10000
    s.lots['L']=Lot('L','P',s.day,s.day+timedelta(days=90),100,6)
    s.demand['D']=Demand('D','P','C',s.day,s.day+timedelta(days=2),6)
    p=Purchase(s.day,'S','P',6);settings=PlannerSettings(horizon_days=14)
    bundle=ForecastBundle('mean8',{}, {}, [])
    a=project(s,settings,[p],bundle=bundle);b=project(s,settings,defer_line([p],p),bundle=bundle)
    assert compare_dispatch(a,b)==[]
    assert a.state.demand['D'].on_time==b.state.demand['D'].on_time==6
    # Six units committed seven days later: 6 * 100 cents * 7 stock/pipeline days.
    investment=lambda op:sum(x['stock_cents']+x['incoming_cents'] for x in op.balances)
    assert investment(a)-investment(b)==4200
    assert a.audit()==b.audit()==[]


def test_deferral_cannot_hide_a_missed_whole_line():
    s=example();s.customers['C']=Customer('C',False,0,14)
    s.demand['D']=Demand('D','P','C',s.day,s.day+timedelta(days=2),6)
    p=Purchase(s.day,'S','P',6);settings=PlannerSettings(horizon_days=14);bundle=ForecastBundle('mean8',{}, {}, [])
    a=project(s,settings,[p],bundle=bundle);b=project(s,settings,defer_line([p],p),bundle=bundle)
    assert compare_dispatch(a,b)[0]['on_time_change']==-6
    assert b.state.demand['D'].cancelled==6


def test_supplier_minimum_repair_is_exact_and_keeps_original_prices():
    from src.replenishment.contracts import PlanRequest,Supplier
    from src.distributor_research.deferrals import repair_today_minimum
    from src.replenishment.physical import validate_purchases
    s=example();s.suppliers['S']=Supplier('S',0,2,1300,100)
    p=Purchase(s.day,'S','P',6)
    repaired=repair_today_minimum(PlanRequest(s),[p],'S')
    assert repaired==[Purchase(s.day,'S','P',18)]
    assert validate_purchases(s,repaired)==[]
    assert p.units==6


def test_before_ordering_loader_excludes_todays_purchases_and_dispatch(operational_path):
    from datetime import date
    from src.replenishment.state import load_snapshot
    from src.demo_data.snapshot import snapshot
    path=operational_path;day=date(2025,6,4)
    s=load_snapshot(path,day,phase='before_ordering');raw=snapshot(path,day,phase='before_ordering')
    assert all(p.placed<day for p in s.incoming.values())
    assert sum(l.units for l in s.lots.values())==sum(r['quantity_units'] for r in raw['snapshot_stock'])
    assert any(d.created==day for d in s.demand.values())


def test_later_history_changes_cannot_change_the_review_snapshot(tmp_path, operational_path):
    from datetime import date
    import shutil,sqlite3
    from src.replenishment.state import load_snapshot
    source=operational_path
    copy=tmp_path/'operational.sqlite';shutil.copy2(source,copy)
    before=load_snapshot(copy,date(2025,6,4),phase='before_ordering').identity()
    with sqlite3.connect(copy) as db:
        db.execute("UPDATE customer_order_lines SET requested_units=requested_units+10000 WHERE known_at>'2025-06-04'")
    assert load_snapshot(copy,date(2025,6,4),phase='before_ordering').identity()==before
