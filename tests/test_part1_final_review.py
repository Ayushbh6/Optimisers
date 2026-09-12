"""Regression evidence for production integration, not just helper execution."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.run_contract import RunConfig
from src.demand.state import DemandState
from src.forecast.state import ForecastState
from src.data.metadata import resolve_metadata
from src.simulation.pipeline import prepare_replay, replay_prepared
from src.simulation.accounting import compare_stock, pending_orders
from src.build_part1 import _policy_config
from src.policy.asof import build_asof_policy_snapshot


def fixture():
    config = RunConfig(Path('.'), Path('/tmp/unused'), observation_start='2025-06-02', initial_learning_end='2025-06-15', replay_start='2025-06-16', observation_end='2025-06-22')
    dates = pd.date_range(config.observation_start, config.observation_end)
    records = []
    for pair in [('a','s'), ('b','t')]:
        for day in dates:
            records.append({'Product No':pair[0], 'Store':pair[1], 'date':day, 'qty_onhand':1., 'stock_known':True,
                'gross_qty_sold':2, 'returned_qty':0, 'unit_cost':10., 'reference_qty_onhand':3.,
                'estimated_demand':2., 'availability_assessment':'available', 'donor_exposure_source':'observed_snapshot_or_flow'})
    daily = pd.DataFrame(records)
    hierarchy = pd.DataFrame({'Product No':['a','b'], 'Store':['s','t'], 'Product Division':['D','D'], 'Product Subcategory':['C','C'], 'effective_date':pd.to_datetime(['2025-06-02']*2)})
    return config, daily, hierarchy


def test_production_feedback_estimates_depletion_without_observing_unfilled_targets():
    config, daily, hierarchy = fixture()
    first = prepare_replay(daily, daily, hierarchy, config)
    altered = daily.copy(); altered.loc[altered.date >= config.replay_start, 'gross_qty_sold'] = 999
    second = prepare_replay(altered, altered, hierarchy, config)
    a, fa, pa, _ = replay_prepared(first, config, _policy_config(config))
    b, fb, pb, _ = replay_prepared(second, config, _policy_config(config))
    # Both shops sell their one available unit on the first day; hidden targets differ.
    pd.testing.assert_frame_equal(fa, fb)
    pd.testing.assert_frame_equal(pa, pb)
    assert a.iloc[0].estimated_demand == 2
    assert a.iloc[0].fulfilled_purchases_units == 1
    assert a.iloc[0].availability_assessment == 'empty_or_depleted'
    assert a.iloc[0].rate_information_cutoff == pd.Timestamp('2025-06-15')


def test_future_sales_returns_costs_categories_and_new_pair_leave_prior_decisions_unchanged():
    config, daily, hierarchy = fixture()
    prepared = prepare_replay(daily, daily, hierarchy, config)
    a, fa, pa, _ = replay_prepared(prepared, config, _policy_config(config))
    altered = daily.copy(); later = altered.date >= '2025-06-20'
    altered.loc[later, ['gross_qty_sold', 'returned_qty', 'unit_cost']] = [99, 7, .5]
    new = altered[later & altered['Product No'].eq('a')].copy(); new['Product No'] = 'future'
    altered = pd.concat([altered,new],ignore_index=True)
    h = pd.concat([hierarchy,pd.DataFrame({'Product No':['a','future'], 'Store':['s','s'], 'Product Division':['NEW','NEW'], 'Product Subcategory':['NEW','NEW'], 'effective_date':pd.to_datetime(['2025-06-20']*2)})],ignore_index=True)
    b, fb, pb, _ = replay_prepared(prepare_replay(altered,altered,h,config),config,_policy_config(config))
    for left,right,date in [(a,b,'date'),(fa,fb,'information_cutoff'),(pa,pb,'as_of')]:
        keys=[date,'Product No','Store']
        left=left[left[date]<'2025-06-20'].sort_values(keys).reset_index(drop=True)
        right=right[right[date]<'2025-06-20'].sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(left,right)


def test_daily_shares_include_incomplete_week_but_fit_excludes_it():
    state=ForecastState([('a','s'),('b','s')]); h=pd.DataFrame({'Product No':['a','b'],'Product Division':['D']*2,'Product Subcategory':['C']*2})
    for day in pd.date_range('2025-06-02',periods=7):state.add(day,[1,1])
    before=state.snapshot(h,'2025-06-08')
    state.add('2025-06-09',[10,0]);after=state.snapshot(h,'2025-06-09')
    assert after.iloc[0].daily_expected_demand > before.iloc[0].daily_expected_demand
    assert after.weekly_expected_demand.sum() == pytest.approx(14)
    assert after.daily_expected_demand.sum()*7 == pytest.approx(14)
    assert after.four_week_expected_demand.sum() == pytest.approx(56)


def test_future_only_cost_keeps_unavailable_policy_row_and_invalid_latest_uses_prior():
    forecast=pd.DataFrame({'Product No':['a','b'],'Store':['s','s'],'daily_expected_demand':[1,1],'demand_std':[0,0],'information_cutoff':pd.to_datetime(['2025-06-02']*2)})
    costs=pd.DataFrame({'Product No':['a','b','b'],'Store':['s']*3,'date':pd.to_datetime(['2025-06-03','2025-06-01','2025-06-02']),'unit_cost_as_of':[9,.5,np.nan]})
    result=build_asof_policy_snapshot(forecast,costs)
    assert len(result)==2
    assert result.iloc[0].policy_status=='unavailable_missing_cost'
    assert result.iloc[1].unit_cost_as_of==.5


def test_accounting_same_scope_rate_store_batches_and_pending_delays():
    config,daily,h=fixture()
    ledger,_,_,_=replay_prepared(prepare_replay(daily,daily,h,config),config,_policy_config(config))
    comparison=compare_stock(ledger,daily,config).iloc[0]
    assert comparison.reference_holding_cost_eur == pytest.approx(2*7*3*10*.2/365)
    assert comparison.reference_capital_eur == 60
    assert comparison.order_batches == len(ledger[ledger.order_qty_units>0][['date','Store']].drop_duplicates())
    assert comparison.batch_cost_eur == comparison.order_batches*50
    changed=compare_stock(ledger,daily,replace(config,holding_rate=.3)).iloc[0]
    assert changed.reference_holding_cost_eur == pytest.approx(comparison.reference_holding_cost_eur*1.5)
    assert changed.simulated_matched_holding_cost_eur == pytest.approx(comparison.simulated_matched_holding_cost_eur*1.5)
    pending=pending_orders(ledger)
    assert (pending.order_arrival_date-pending.date).dt.days.eq(10).all()
    assert pending.order_qty_units.sum()==ledger[ledger.date==ledger.date.max()].on_order_units.sum()
    assert pd.isna(comparison.total_cost_savings_eur)


def test_late_anchor_in_production_excludes_only_prior_days_and_initialises_once():
    config,daily,h=fixture()
    late=daily['Product No'].eq('b') & (daily.date<'2025-06-18')
    daily.loc[late,'stock_known']=False;daily.loc[late,'qty_onhand']=np.nan
    daily.loc[(daily['Product No']=='b') & (daily.date=='2025-06-18'),'qty_onhand']=7
    ledger,_,_,_=replay_prepared(prepare_replay(daily,daily,h,config),config,_policy_config(config))
    pair=ledger[ledger['Product No']=='b']
    assert not pair[pair.date<='2025-06-18'].eligible.any()
    assert pair[pair.date=='2025-06-19'].iloc[0].opening_on_hand_units==7
    assert pair[pair.date=='2025-06-20'].iloc[0].opening_on_hand_units==5


def test_production_order_up_to_moq_delay_and_no_stock_disposal():
    config,daily,h=fixture();config=replace(config,lead_time_days=2)
    ledger,_,policy,_=replay_prepared(prepare_replay(daily,daily,h,config),config,_policy_config(config))
    first=ledger[(ledger.date==pd.Timestamp(config.replay_start)) & (ledger['Product No']=='a')].iloc[0]
    rule=policy[(policy.as_of==pd.Timestamp(config.replay_start)) & (policy['Product No']=='a')].iloc[0]
    assert first.order_qty_units==max(5,rule.order_up_to_S-first.decision_inventory_position_units)
    assert ledger[(ledger.date=='2025-06-18') & (ledger['Product No']=='a')].iloc[0].arrivals_units==first.order_qty_units
    assert ledger[ledger.order_qty_units>0].order_qty_units.ge(5).all()
    assert ledger.mass_balance_residual_units.fillna(0).eq(0).all()


def test_reproducible_raw_build_has_identical_numerical_artifacts(tmp_path):
    from tests.test_part1_pipeline import _raw_fixture
    from src.build_part1 import run_part1
    _raw_fixture(tmp_path)
    config=RunConfig(tmp_path,tmp_path/'one',observation_start='2025-06-01',initial_learning_end='2026-01-15',replay_start='2026-01-16',observation_end='2026-01-18')
    a=run_part1(config);b=run_part1(replace(config,output_dir=tmp_path/'two'))
    for name in a:
        if name.endswith('.parquet'):
            pd.testing.assert_frame_equal(pd.read_parquet(a[name]),pd.read_parquet(b[name]))


def test_invalid_return_flag_and_nonfinite_quantity_are_rejected():
    from src.data.loader import validate_sales_transactions
    for quantity, flag in [(1, 'unknown'), (np.inf, 0)]:
        with pytest.raises(ValueError):
            validate_sales_transactions(pd.DataFrame({'Qty Sold':[quantity], 'Is Return':[flag]}))


def test_cost_and_price_facts_are_available_without_stock_anchor():
    from src.data.reconstruction import reconstruct_daily_onhand
    from src.data.config import DataConfig
    inv = pd.DataFrame({'Product No':['a'], 'Store':['s'], 'Start Date':pd.to_datetime(['2025-06-01']),
        'End Date_parsed':pd.to_datetime(['2025-06-03']), 'Qty on hand':[np.nan],
        'Stock Unit Cost Price':[2.], 'Stock Unit Selling Price':[4.], 'Stock Status':['Full']})
    sales = pd.DataFrame(columns=['Product No','Store','date','Qty Sold'])
    daily,_=reconstruct_daily_onhand(inv,sales,DataConfig(observation_end_date='2025-06-03'))
    assert daily.qty_onhand.isna().all()
    assert daily.unit_cost.eq(2).all()
    assert daily.unit_selling_price.eq(4).all()


def test_run_rejects_raw_input_mutation_before_manifest(tmp_path, monkeypatch):
    from tests.test_part1_pipeline import _raw_fixture
    import src.build_part1 as runner
    _raw_fixture(tmp_path)
    original = runner._write_report
    def changed_input(*args, **kwargs):
        original(*args, **kwargs)
        with (tmp_path/'data/raw/retail_sales_ml_apl.csv').open('a') as handle:
            handle.write('\n')
    monkeypatch.setattr(runner, '_write_report', changed_input)
    config=RunConfig(tmp_path,tmp_path/'run',observation_end='2026-01-18')
    with pytest.raises(RuntimeError, match='Raw inputs changed'):
        runner.run_part1(config)
    assert not (config.output_dir/'run_manifest.json').exists()


def test_hand_calculated_model_intervals_and_preupdate_residuals():
    from src.forecast.models import croston_forecast, tsb_forecast
    rate, error = croston_forecast(np.array([3.,0.,0.,3.]), alpha=1)
    assert rate == 1  # Three periods between purchases of three units.
    assert error == pytest.approx(np.sqrt(18/4))
    rate, error = tsb_forecast(np.array([2.,0.,6.]), alpha=1, beta=1)
    assert rate == 6
    # First observation initialises; subsequent predictions are 2 and 0.
    assert error == pytest.approx(np.sqrt(40/3))
    rate, _ = tsb_forecast(np.array([2.] + [0.] * 100), beta=.1)
    assert rate == pytest.approx(2 * .9**100)


def test_seventh_same_day_donor_is_not_available_to_another_pair_until_tomorrow():
    state = DemandState([('a','s'),('b','s')])
    categories = [('D','C'),('D','C')]
    for _ in range(6):state.step([1,0],[True,True],[True,False],categories)
    estimate, method, _, _ = state.step([1,0],[True,True],[True,False],categories)
    assert estimate[1] == 0 and method[1] == 'insufficient_prior_rate'
    estimate, _, donors, _ = state.step([1,0],[True,True],[True,False],categories)
    assert estimate[1] == 1 and donors[1] == 7
