"""Rebuild Part 1 from raw ledgers; use --sensitivity for all 27 settings."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
import json
import pandas as pd
from src.data.config import DataConfig
from src.data.loader import load_inventory_data, load_sales_data
from src.data.reconstruction import reconstruct_daily_onhand
from src.data.metadata import metadata_events
from src.demand.asof import estimate_demand_asof
from src.demand.config import DemandConfig
from src.forecast.asof import evaluate_forecast_benchmarks
from src.policy.config import PolicyConfig
from src.run_contract import RunConfig, default_run_config, write_manifest, source_identity, sha256_file, sha256_file
from src.simulation.pipeline import prepare_replay, replay_prepared
from src.simulation.accounting import compare_stock, replay_breakdown, pending_orders


def _policy_config(config: RunConfig) -> PolicyConfig:
    return PolicyConfig(project_root=config.project_root, artifacts_dir=config.output_dir,
        supplier_lead_time_days=config.lead_time_days, target_service_level=config.service_level,
        annual_holding_cost_rate=config.holding_rate, min_order_quantity=config.min_order_quantity,
        reorder_cost_fixed=config.batch_order_cost, reorder_cost_line_item=config.line_order_cost,
        stocking_demand_threshold=config.stocking_threshold)


def _run_replay(daily, demand, hierarchy, config, policy_config):
    """Compatibility entrypoint around the single production controller."""
    return replay_prepared(prepare_replay(daily, demand, hierarchy, config), config, policy_config)


_replay_breakdown = replay_breakdown


def run_part1_sensitivity(daily: pd.DataFrame, demand: pd.DataFrame, hierarchy: pd.DataFrame, config: RunConfig, *, prepared=None) -> pd.DataFrame:
    """Run every retained setting with an independent copy of initial learning."""
    prepared = prepared or prepare_replay(daily, demand, hierarchy, config)
    records = []
    for lead in config.sensitivity_lead_times:
        for service in config.sensitivity_service_levels:
            for rate in config.sensitivity_holding_rates:
                scenario = replace(config, lead_time_days=lead, service_level=service, holding_rate=rate)
                ledger, _, _, metrics = replay_prepared(prepared, scenario, _policy_config(scenario), traces=False)
                comparison = compare_stock(ledger, daily, scenario).iloc[0].to_dict()
                records.append({'scenario_id': len(records) + 1, 'lead_time_days': lead, 'target_service_level': service,
                    **comparison, 'ending_stock_units': metrics['ending_on_hand_units'],
                    'pending_order_units': int(pending_orders(ledger).order_qty_units.sum()),
                    'holding_cost_eur': comparison['simulated_matched_holding_cost_eur'],
                    'capital_tied_up_eur': comparison['simulated_matched_capital_eur']})
                del ledger
                print(f'Sensitivity {len(records)}/27 completed: lead={lead}, service={service}, holding={rate}', flush=True)
    return pd.DataFrame(records)


def _write_report(config, metrics, comparisons, benchmarks, excluded, breakdown, sensitivity):
    full = comparisons.iloc[0]
    lines = ['# Part 1 recorded-purchase replay', '',
        'Estimated demand is an estimate, not verified customer demand. These dates are development evaluation dates.', '',
        f'Observation: {config.observation_start}–{config.observation_end}. Initial learning through {config.initial_learning_end}.',
        f'Replay: {config.replay_start}–{config.observation_end}; empty opening order book assumed.', '',
        f"Recorded purchases in eligible scope: {metrics['total_target_units']}; fulfilled: {metrics['total_fulfilled_units']}; unfulfilled: {metrics['total_unfulfilled_units']}.",
        f"Observed-purchase coverage: {metrics['observed_purchase_coverage']}. Historical reference is 100% by construction, not a true customer fill rate.",
        f"Ending stock: {metrics['ending_on_hand_units']} whole units. Excluded earlier purchases: {int(excluded.excluded_recorded_purchase_units.sum())} units.",
        'When coverage falls, the result cannot be described as “same sales”.',
        f"Simulated ordering cost: EUR {full.ordering_cost_eur:.2f} (store-day batches {full.batch_cost_eur:.2f}; order lines {full.line_cost_eur:.2f}).",
        'Historical ordering cost and total-cost savings: unavailable without defensible purchase-order records.', '',
        '## Matched comparisons', '',
        'Both sides use the same dated pair cost and exactly the same known-stock pair-days. Partial capital totals are not full-chain capital.', '',
        comparisons.to_markdown(index=False), '', '## Historical forecast evaluation', '',
        'Model and baselines use identical dates and target rows. Observed purchases and estimated demand are separate scores. Bounds are an uncalibrated normal approximation; daily scaling assumes independent days.', '',
        benchmarks.to_markdown(index=False), '', '## Division/store breakdown', '', breakdown.to_markdown(index=False), '',
        'Pending order lines and exact due dates are in pending_orders.parquet. Day-end historical returns are an assumed external stream, not linked to simulated sales.', '',
        f'Sensitivity: {0 if sensitivity is None else len(sensitivity)} of 27 full-data settings executed in this run.',
        'Part 2 prerequisites: better policies, realistic missed-demand trials, operational assumptions, and independent validation before any website savings claim.']
    config.artifact_path('part1_report.md').write_text('\n'.join(lines) + '\n')


def run_part1(config: RunConfig, *, run_sensitivity: bool = False) -> dict[str, Path]:
    """Build all stages without reading legacy artifacts or overwriting a run."""
    config.validate()
    source_before = source_identity(Path(__file__).resolve().parent.parent)
    input_before = None
    if config.output_dir.exists() and any(config.output_dir.iterdir()):
        raise FileExistsError(f'Output must be a fresh directory: {config.output_dir}')
    inputs_before = {str(path): sha256_file(path) for path in (config.sales_path, config.inventory_path)}
    config.output_dir.mkdir(parents=True, exist_ok=True)
    data_config = DataConfig(project_root=config.project_root, raw_dir=config.raw_dir,
        sales_csv_path=config.sales_path, inventory_csv_path=config.inventory_path,
        observation_start_date=config.observation_start, observation_end_date=config.observation_end)
    input_before = {str(path): sha256_file(path) for path in (config.sales_path, config.inventory_path)}
    inventory = load_inventory_data(data_config); sales = load_sales_data(data_config)
    sales = sales[sales['Transaction Date'].between(config.observation_start, config.observation_end)].copy()
    inventory = inventory[inventory['Start Date'] <= pd.Timestamp(config.observation_end)].copy()
    hierarchy = metadata_events(inventory, sales)
    source_counts = {'source_transaction_rows': len(sales), 'source_signed_units': float(sales['Qty Sold'].sum()),
        'source_gross_units': float(sales['Qty Sold'].clip(lower=0).sum()),
        'source_returned_units': float(-sales['Qty Sold'].clip(upper=0).sum())}
    daily, stats = reconstruct_daily_onhand(inventory, sales, data_config)
    daily = daily[daily.date.between(config.observation_start, config.observation_end)].copy()
    artifacts = {}
    def save(name, data):
        path = config.artifact_path(name + '.parquet')
        data.to_parquet(path, index=False, engine='pyarrow'); artifacts[path.name] = path
    if daily.net_qty_sold.sum() != source_counts['source_signed_units']:
        raise AssertionError('Raw signed quantities do not reconcile')
    if daily.gross_qty_sold.sum() != source_counts['source_gross_units'] or daily.returned_qty.sum() != source_counts['source_returned_units']:
        raise AssertionError('Raw purchases or returns do not reconcile')
    save('daily_onhand', daily)
    daily = daily[['Product No', 'Store', 'date', 'qty_onhand', 'stock_known', 'gross_qty_sold', 'returned_qty', 'net_qty_sold', 'unit_cost', 'reference_qty_onhand', 'raw_qty_onhand', 'source', 'reconciliation_adjustment', 'unexplained_shortfall', 'stock_discrepancy_unresolved']].copy()
    print('Stock rebuilt', flush=True)
    demand = estimate_demand_asof(daily, hierarchy, config=DemandConfig(min_in_stock_days_sku_store=config.minimum_exposure_days))
    save('demand', demand)
    demand = demand[['Product No', 'Store', 'date', 'estimated_demand', 'gross_qty_sold', 'stock_known', 'availability_assessment', 'donor_exposure_source']].copy()
    daily = daily[['Product No', 'Store', 'date', 'qty_onhand', 'stock_known', 'gross_qty_sold', 'returned_qty', 'net_qty_sold', 'unit_cost', 'reference_qty_onhand']].copy()
    print('Demand rebuilt', flush=True)
    detail, summary = evaluate_forecast_benchmarks(demand, hierarchy, pd.date_range(config.replay_start, config.observation_end),
        observed_column='gross_qty_sold', method=config.forecast_method, alpha=config.alpha, beta=config.beta, laplace_prior=config.laplace_prior)
    save('forecast_benchmark_detail', detail); save('forecast_benchmark_summary', summary)
    del detail
    print('Historical benchmarks completed', flush=True)
    prepared = prepare_replay(daily, demand, hierarchy, config)
    ledger, forecast, policy, metrics = replay_prepared(prepared, config, _policy_config(config))
    save('forecast', forecast); save('policy', policy); save('replay_ledger', ledger)
    del forecast, policy
    comparisons = compare_stock(ledger, daily, config); save('matched_comparisons', comparisons)
    breakdown = replay_breakdown(ledger); save('replay_breakdown', breakdown)
    save('pending_orders', pending_orders(ledger))
    excluded = ledger[~ledger.eligible].groupby(['Product No', 'Store'], as_index=False).agg(excluded_recorded_purchase_units=('recorded_gross_purchases_units', 'sum'), excluded_pair_days=('eligible', 'size'))
    save('excluded_purchases', excluded)
    if ledger.mass_balance_residual_units.fillna(0).ne(0).any():
        raise AssertionError('Replay stock conservation failed')
    if int(breakdown.ending_stock_units.sum()) != metrics['ending_on_hand_units']:
        raise AssertionError('Ending stock breakdown failed')
    if int(ledger.recorded_gross_purchases_units.sum()) != int(daily.loc[daily.date >= pd.Timestamp(config.replay_start), 'gross_qty_sold'].sum()):
        raise AssertionError('Replay/excluded purchase reconciliation failed')
    acceptance = {**source_counts, 'gross_purchase_units': int(daily.gross_qty_sold.sum()), 'returned_units': int(daily.returned_qty.sum()),
        'daily_rows': len(daily), 'replay_rows': len(ledger), 'stock_conservation_failures': 0,
        'eligible_recorded_purchase_units': metrics['total_target_units'], 'fulfilled_units': metrics['total_fulfilled_units'],
        'ending_stock_units': metrics['ending_on_hand_units'], 'breakdown_ending_stock_units': int(breakdown.ending_stock_units.sum()),
        'excluded_purchase_units': int(excluded.excluded_recorded_purchase_units.sum())}
    del ledger
    print('Main replay and matched accounting completed', flush=True)
    sensitivity = run_part1_sensitivity(daily, demand, hierarchy, config, prepared=prepared) if run_sensitivity else None
    if sensitivity is not None:
        save('sensitivity', sensitivity)
    _write_report(config, metrics, comparisons, summary, excluded, breakdown, sensitivity)
    artifacts['part1_report.md'] = config.artifact_path('part1_report.md')
    limitations = ['empty opening orders assumed', 'external day-end returns assumed', 'stock bridges assume no unobserved receipts', 'historical ordering cost and total savings unavailable', 'normal uncertainty approximation is not calibrated', 'capital comparison covers matched known-stock/cost pair-days only']
    acceptance['sensitivity_scenarios_completed'] = 0 if sensitivity is None else len(sensitivity)
    acceptance_path = config.artifact_path('acceptance_checks.json')
    acceptance_path.write_text(json.dumps(acceptance, indent=2) + '\n')
    artifacts[acceptance_path.name] = acceptance_path
    source_after = source_identity(Path(__file__).resolve().parent.parent)
    if {k:v for k,v in source_before.items() if k.startswith('src/')} != {k:v for k,v in source_after.items() if k.startswith('src/')}:
        raise RuntimeError('Implementation changed during the run; rebuild with stable source')
    if inputs_before != {str(path): sha256_file(path) for path in (config.sales_path, config.inventory_path)}:
        raise RuntimeError('Raw inputs changed during the run; rebuild with stable inputs')
    if input_before != {str(path): sha256_file(path) for path in (config.sales_path, config.inventory_path)}:
        raise RuntimeError("Raw inputs changed during the run")
    write_manifest(config, artifacts, limitations)
    return artifacts


def main() -> int:
    """Command shared by all stage wrappers; fresh output directory is mandatory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--sensitivity', action='store_true')
    args = parser.parse_args()
    run_part1(default_run_config(output_dir=args.output_dir.resolve()), run_sensitivity=args.sensitivity)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
