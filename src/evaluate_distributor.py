"""Verification, freeze and reserved evaluation for the approved distributor demo.

This command is private evaluation tooling, never part of the public web service.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic

from src.demo_data.config import EVALUATION_SEEDS, SCENARIO_FAMILIES, default_config
from src.demo_data.storage import validate_output
from src.replenishment.cli import write_new
from src.replenishment.contracts import PlannerSettings
from src.replenishment.evaluator import run_policy
from src.replenishment.scenarios import frozen_identity, materialise, verify_freeze


def runner_hash() -> str:
    """Include this orchestration and gate code in the evaluation identity."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def verification(folder: Path) -> None:
    """Run tests inside the repository and retain a compact signed-by-hash record."""
    folder = validate_output(folder)
    folder.mkdir(parents=True, exist_ok=True)
    before = frozen_identity()
    command = [sys.executable, '-m', 'pytest', 'tests', '-q',
               f'--basetemp={folder / "test-work"}']
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    record = dict(command=command, exit_code=result.returncode, output=result.stdout,
                  sources=before, runner_sha256=runner_hash())
    write_new(folder/'verification.json', record)
    if result.returncode or before != frozen_identity():
        raise RuntimeError('Tests failed or numerical sources changed during verification')
    print(result.stdout, flush=True)


def freeze(development: Path, output: Path) -> None:
    """Record the final method before any reserved business outcomes are generated."""
    summary = json.loads((development/'optimiser'/'summary.json').read_text())
    selection = json.loads((development/'baseline-selection.json').read_text())
    verified = json.loads((development/'verification.json').read_text())
    if len(summary['cases']) != 18 or any(c['audit_errors'] for c in summary['cases']):
        raise ValueError('All 18 development cases must finish with zero audit errors')
    if summary['sources'] != frozen_identity() or verified['sources'] != frozen_identity():
        raise ValueError('Development results and tests must match the current numerical implementation')
    if verified['exit_code'] != 0 or verified['runner_sha256'] != runner_hash():
        raise ValueError('Verification must pass for the current evaluation runner')
    write_new(output, dict(sources=frozen_identity(), runner_sha256=runner_hash(),
        settings=selection['settings'], development_case_count=18, development_audits_passed=True,
        families=SCENARIO_FAMILIES, reserved_seeds=EVALUATION_SEEDS,
        sensitivities={'delay': 'Actual supplier deliveries two workdays later; notices released causally',
                       'freshness': 'Actual future incoming freshness capped at 30 days; revealed on receipt'},
        acceptance='docs/DISTRIBUTOR_IMPLEMENTATION_PLAN.md',
        synthetic_label='SYNTHETIC DEMONSTRATION DATA — NOT CLIENT RECORDS'))


def paired_case(folder: str, settings: dict, family: str, seed: int, sensitivity: str) -> dict:
    """Compare both policies under identical actual conditions and planner knowledge."""
    started = monotonic()
    kwargs = dict(delay_days=2 if sensitivity == 'delay' else 0,
                  freshness_days=30 if sensitivity == 'freshness' else None)
    # These are unannounced adverse conditions. Both planners retain the same
    # prior assumptions and learn actual dates/freshness only from released records.
    baseline = run_policy(Path(folder), PlannerSettings(**settings), 'baseline', **kwargs)
    optimiser = run_policy(Path(folder), PlannerSettings(**settings), 'optimiser', **kwargs)
    return dict(family=family, seed=seed, sensitivity=sensitivity, baseline=baseline, optimiser=optimiser,
                elapsed_seconds=monotonic()-started)


def permitted_tail(actual: float, baseline: float) -> bool:
    """Five percent tolerance, with a €25 absolute allowance near zero."""
    return actual <= baseline + max(0.05*baseline, 2500)


def assess(rows: list[dict]) -> dict:
    """Apply the approved gate without inventing a favourable aggregate score."""
    families = {}
    severe, errors = [], []
    for family in SCENARIO_FAMILIES:
        subset = [r for r in rows if r['family'] == family]
        wins, comparisons, line_changes = 0, [], []
        for row in subset:
            a, b = row['optimiser']['settled'], row['baseline']['settled']
            service_change = a['service']-b['service']
            line_changes.append(a['complete_line_service']-b['complete_line_service'])
            service_route = service_change >= .02-1e-9 and a['investment_cents'] <= 1.05*b['investment_cents']
            stock_route = b['investment_cents'] > 0 and a['investment_cents'] <= .90*b['investment_cents'] and service_change >= -.01-1e-9
            tail_ok = permitted_tail(a['expiry_cents'], b['expiry_cents']) and permitted_tail(
                a['ending_investment_cents'], b['ending_investment_cents'])
            win = (service_route or stock_route) and tail_ok
            wins += win
            if service_change < -.05-1e-9:
                severe.append(dict(family=family, seed=row['seed'], service_change_points=100*service_change))
            if row['optimiser']['audit_errors'] or row['baseline']['audit_errors']:
                errors.append(dict(family=family, seed=row['seed']))
            comparisons.append(dict(seed=row['seed'], service_change_points=100*service_change,
                baseline_investment_cents=b['investment_cents'], optimiser_investment_cents=a['investment_cents'],
                service_route=service_route, stock_route=stock_route, tail_ok=tail_ok, qualifying=win))
        mean_line_change = sum(line_changes)/len(line_changes) if line_changes else 0
        families[family] = dict(case_count=len(subset), qualifying_seeds=wins,
            complete_line_change_points=100*mean_line_change,
            qualifies=family != 'ample_stock' and len(subset) == 5
            and {r['seed'] for r in subset} == set(EVALUATION_SEEDS)
            and wins >= 4 and mean_line_change >= -.01-1e-9,
            cases=comparisons)
    winning = [family for family, row in families.items() if row['qualifies']]
    return dict(quantitative_pass=len(rows) == 30 and len(winning) >= 2 and not severe and not errors,
                winning_families=winning, families=families, severe_regressions=severe, audit_failures=errors,
                claim_boundary='Synthetic scenario results only; not achieved client savings')


def reserved(freeze_path: Path, output: Path, *, workers: int = 4) -> None:
    """Open reserved cases once, preserving unfavourable results and source hashes."""
    contract = verify_freeze(freeze_path)
    if contract['runner_sha256'] != runner_hash():
        raise ValueError('Evaluation runner differs from the frozen version')
    output = validate_output(output)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output/'run-contract.json', contract)
    work = output/'work'
    work.mkdir()
    cases = []
    for family in SCENARIO_FAMILIES:
        for seed in EVALUATION_SEEDS:
            folder = work/f'{family}-{seed}'
            audit = materialise(default_config(family, seed), folder, freeze_path=freeze_path)
            write_new(folder/'audit.json', audit)
            cases.append((family, seed, folder))
    assessments = {}
    for sensitivity in ('nominal', 'delay', 'freshness'):
        rows = []
        stage = output/sensitivity
        stage.mkdir()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(paired_case, str(folder), contract['settings'], family, seed, sensitivity): (family, seed)
                       for family, seed, folder in cases}
            for future in as_completed(futures):
                row = future.result()
                verify_freeze(freeze_path)
                write_new(stage/f'{row["family"]}-{row["seed"]}.json', row)
                rows.append(row)
                a, b = row['optimiser']['settled'], row['baseline']['settled']
                print(f'{sensitivity} {row["family"]}/{row["seed"]}: service {(a["service"]-b["service"])*100:+.2f} points', flush=True)
        assessment = assess(rows)
        assessments[sensitivity] = assessment
        write_new(stage/'assessment.json', assessment)
        # Once nominal performance fails, no improvement claim can pass. Preserve
        # all 30 nominal cases; avoid spending computation polishing a failed claim.
        if sensitivity == 'nominal' and not assessment['quantitative_pass']:
            break
    robust = all(s in assessments and assessments[s]['quantitative_pass'] for s in ('nominal', 'delay', 'freshness'))
    if robust:
        winning = set(assessments['nominal']['winning_families'])
        robust = len(winning & set(assessments['delay']['winning_families']) & set(assessments['freshness']['winning_families'])) >= 2
    write_new(output/'release-gate.json', dict(nominal_pass=assessments['nominal']['quantitative_pass'],
        robust_pass=robust, completed_sensitivities=list(assessments),
        permitted_to_claim_synthetic_improvement=assessments['nominal']['quantitative_pass'] and robust,
        ui_and_buyer_workflow_acceptance='Separate; not established by this report'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['verify', 'freeze', 'reserved'])
    parser.add_argument('--development', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    if args.stage == 'verify':
        verification(args.development)
    elif args.stage == 'freeze':
        freeze(args.development, args.output)
    else:
        reserved(args.freeze, args.output, workers=args.workers)


if __name__ == '__main__':
    main()
