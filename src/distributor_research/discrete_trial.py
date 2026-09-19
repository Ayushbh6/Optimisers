"""Freeze and run the four-case adaptive discrete-search trial."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
from time import monotonic

from src.demo_data.config import default_config
from src.demo_data.generator import generate_scenario
from src.demo_data.storage import validate_output
from src.replenishment.cli import write_new
from src.replenishment.contracts import PlannerSettings
from src.replenishment.discrete import SearchBounds
from src.replenishment.evaluator import run_policy

from .checkpoints import archive_sources, exclusive_batch


CASES = (
    ('ordinary', 1101),
    ('restricted_spending', 1101),
    ('supplier_disruption', 1101),
    ('ample_stock', 1101),
)
HYPOTHESIS = (
    'Exact physical replay of bounded supplier-basket edits, with future stock-cover decisions recalculated '
    'from each evolving candidate state, can reduce average stock plus commitments without reducing the '
    'deliveries achieved by the independently evolving stock-cover policy.'
)


def source_identity() -> dict[str, str]:
    """Hash numerical code, hand tests and fixed business contracts."""
    paths = list(Path('src/demo_data').glob('*.py')) + list(Path('src/replenishment').glob('*.py'))
    paths += [Path('src/distributor_research/discrete_trial.py'),
              Path('tests/test_distributor_discrete.py'), Path('tests/test_distributor_planner_risk.py'),
              Path('docs/DISTRIBUTOR_DISCRETE_DIAGNOSIS_01.md'),
              Path('docs/DISTRIBUTOR_IMPLEMENTATION_PLAN.md'),
              Path('docs/DISTRIBUTOR_ITERATION_PROTOCOL.md'), Path('requirements.txt'), Path('pytest.ini')]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def contract() -> dict:
    """Return the outcome-blind scope fixed before any case is generated."""
    return dict(
        synthetic=True,
        development_only=True,
        hypothesis=HYPOTHESIS,
        cases=[dict(family=family, seed=seed) for family, seed in CASES],
        case_selection='The first declared development seed for each of the four user-required families',
        settings=asdict(PlannerSettings(forecast_method='mean8', safety_workdays=0)),
        search_bounds=asdict(SearchBounds()),
        future_policy=('Commit only today\'s candidate basket; in every demand view, recalculate competent '
                       'stock cover at each later supplier decision from that replay\'s physical state.'),
        comparison=('Both policies start from the same immutable generated records and evolve independently; '
                    'each decision commits only that policy\'s current-day purchases.'),
        stop='Report these four cases only; do not start the 18-case batch or open seeds 91301-91305.',
        sources=source_identity(),
    )


def freeze(root: Path) -> None:
    """Write the immutable four-case contract before reading any outcomes."""
    root = validate_output(root)
    root.mkdir(parents=True, exist_ok=False)
    frozen = contract()
    write_new(root/'contract.json', frozen)
    archive_sources(root, frozen['sources'])
    print(json.dumps({'frozen': True, 'cases': frozen['cases'], 'output': str(root)}, indent=2))


def _regressions(optimiser: dict, baseline: dict) -> dict:
    output = {}
    for group in ('customer', 'product'):
        before, after = baseline['breakdown'][group], optimiser['breakdown'][group]
        if before.keys() != after.keys():
            raise ValueError(f'{group} comparison groups differ')
        rows = []
        for key in sorted(before):
            if before[key]['requested'] != after[key]['requested']:
                raise ValueError(f'{group} requested quantities differ: {key}')
            on_time = after[key]['on_time']-before[key]['on_time']
            shipped = after[key]['shipped']-before[key]['shipped']
            if on_time < 0 or shipped < 0:
                rows.append(dict(id=key, requested=before[key]['requested'],
                                 on_time_change=on_time, shipped_change=shipped))
        output[group] = rows
    return output


def _decision(row: dict) -> dict:
    search = row.get('sensitivity', {}).get('simulation_search', {})
    selected = search.get('selected_candidate')
    return dict(
        day=row['day'],
        recommended=row.get('recommended'),
        purchases=row['purchases'],
        generated_candidates=search.get('generation', {}).get('feasible_candidates'),
        preflight_rejections=len(search.get('generation', {}).get('preflight_rejections', [])),
        replay_count=search.get('replay_count'),
        runtime_seconds=search.get('elapsed_seconds'),
        future_policy=search.get('future_policy'),
        survivors=search.get('survivors'),
        improving_survivors=search.get('improving_survivors'),
        selected_changes=selected.get('changes', []) if selected else [],
        selected_cash_required_cents=search.get('selected_cash_required_cents'),
        selected_arrivals=[dict(product=item['product'], units=item['units'],
                                expected_arrival=item['expected_arrival'])
                           for item in search.get('selected_today_basket', [])],
        delivery_risks=search.get('delivery_risks', []),
        leftover_consequences=search.get('leftover_consequences'),
        rejection_reasons=[dict(candidate_id=item['candidate_id'],
                                changes=item['changes'], reasons=item['rejection_reasons'])
                           for item in search.get('candidate_outcomes', []) if not item['accepted']],
    )


def _case_report(family: str, seed: int, manifest: dict, baseline: dict,
                 optimiser: dict, elapsed: dict) -> dict:
    """Retain compact complete outcomes without large generated databases."""
    regressions = _regressions(optimiser, baseline)
    before, after = baseline['settled'], optimiser['settled']
    return dict(
        family=family,
        seed=seed,
        input_manifest=manifest,
        elapsed_seconds=elapsed,
        baseline=dict(primary=baseline['primary'], settled=before,
                      final_stock_cents=baseline['final_stock_cents'],
                      final_incoming_cents=baseline['final_incoming_cents'],
                      settlement_expiry_cents=baseline['settlement_expiry_cents'],
                      unresolved_supplier_units=baseline['unresolved_supplier_units'],
                      audit_errors=baseline['audit_errors'], decisions=len(baseline['decisions'])),
        optimiser=dict(primary=optimiser['primary'], settled=after,
                       final_stock_cents=optimiser['final_stock_cents'],
                       final_incoming_cents=optimiser['final_incoming_cents'],
                       settlement_expiry_cents=optimiser['settlement_expiry_cents'],
                       unresolved_supplier_units=optimiser['unresolved_supplier_units'],
                       audit_errors=optimiser['audit_errors'], decisions=[_decision(row) for row in optimiser['decisions']]),
        change=dict(
            service_points=100*(after['service']-before['service']),
            complete_line_service_points=100*(after['complete_line_service']-before['complete_line_service']),
            investment_cents=after['investment_cents']-before['investment_cents'],
            investment_fraction=(after['investment_cents']/before['investment_cents']-1
                                 if before['investment_cents'] else None),
            expiry_cents=after['expiry_cents']-before['expiry_cents'],
            ending_investment_cents=after['ending_investment_cents']-before['ending_investment_cents'],
        ),
        regressions=regressions,
    )


def _summary(rows: list[dict]) -> dict:
    cases = []
    for row in rows:
        decisions = row['optimiser']['decisions']
        cases.append(dict(
            family=row['family'], seed=row['seed'], change=row['change'],
            customer_regressions=len(row['regressions']['customer']),
            product_regressions=len(row['regressions']['product']),
            changed_decisions=sum(d['recommended'] == 'Simulation-checked basket' for d in decisions),
            total_decisions=len(decisions),
            candidates_replayed=sum(d['replay_count'] or 0 for d in decisions),
            search_runtime_seconds=sum(d['runtime_seconds'] or 0 for d in decisions),
        ))
    return dict(
        cases=cases,
        all_audits_passed=all(not row['baseline']['audit_errors'] and not row['optimiser']['audit_errors'] for row in rows),
        fresh_evaluation_opened=False,
        full_18_case_batch_started=False,
        permits_savings_claim=False,
    )


def run(root: Path) -> None:
    """Run only the frozen cases, preserving failures and deleting scratch DBs."""
    root = validate_output(root)
    expected = contract()
    if json.loads((root/'contract.json').read_text()) != expected:
        raise ValueError('Frozen case scope, settings or numerical sources changed')
    archive_sources(root, expected['sources'])
    settings = PlannerSettings(**expected['settings'])
    work = root/'work'
    work.mkdir(exist_ok=True)
    cases = root/'cases'
    cases.mkdir(exist_ok=True)
    with exclusive_batch(root):
        rows = []
        for family, seed in CASES:
            target = cases/f'{family}-{seed}.json'
            if target.exists():
                rows.append(json.loads(target.read_text()))
                continue
            folder = work/f'{family}-{seed}'
            if not folder.exists():
                generate_scenario(default_config(family, seed), folder)
            manifest = json.loads((folder/'run_manifest.json').read_text())
            started = monotonic()
            baseline = run_policy(folder, settings, 'baseline')
            baseline_seconds = monotonic()-started
            started = monotonic()
            optimiser = run_policy(folder, settings, 'optimiser')
            optimiser_seconds = monotonic()-started
            if baseline['audit_errors'] or optimiser['audit_errors']:
                raise ValueError(f'{family}/{seed}: accounting failure')
            if source_identity() != expected['sources']:
                raise RuntimeError('Numerical source changed during the frozen test')
            row = _case_report(family, seed, manifest, baseline, optimiser,
                               dict(baseline=baseline_seconds, optimiser=optimiser_seconds))
            write_new(target, row)
            rows.append(row)
            shutil.rmtree(folder)
            print(f'{family}/{seed}: service {row["change"]["service_points"]:+.2f} points; '
                  f'investment {row["change"]["investment_fraction"]:+.2%}; '
                  f'customer regressions {len(row["regressions"]["customer"])}', flush=True)
        summary = _summary(rows)
        target = root/'summary.json'
        if target.exists() and json.loads(target.read_text()) != summary:
            raise ValueError('Existing compact summary differs')
        if not target.exists():
            write_new(target, summary)
        if work.exists() and not any(work.iterdir()):
            work.rmdir()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('freeze', 'run'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    freeze(args.output) if args.command == 'freeze' else run(args.output)
