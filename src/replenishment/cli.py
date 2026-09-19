"""Reproducible development runs; reserved evaluation requires a later freeze."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import date
import hashlib
import json
from pathlib import Path

from src.demo_data.config import DEVELOPMENT_SEEDS, SCENARIO_FAMILIES, default_config
from src.demo_data.generator import generate_scenario
from src.demo_data.storage import validate_output
from .contracts import PlannerSettings
from .evaluator import run_policy
from .forecast import select_method
from .state import load_snapshot


def write_new(path: Path, value: dict) -> None:
    """Never silently replace prior evidence."""
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, default=str)
        handle.write('\n')


def sources() -> dict:
    """Record generator and implementation identities separately."""
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for root in ('src/demo_data', 'src/replenishment')
            for p in sorted(Path(root).glob('*.py'))}


def development(output: Path, *, baseline_only: bool = False) -> None:
    """Build all declared development histories and select the comparison fairly."""
    output = validate_output(output)
    output.mkdir(parents=True, exist_ok=False)
    work = output/'work'
    work.mkdir()
    cases, states = [], []
    for family in SCENARIO_FAMILIES:
        for seed in DEVELOPMENT_SEEDS:
            config = default_config(family, seed)
            folder = work/f'{family}-{seed}'
            generate_scenario(config, folder)
            states.append(load_snapshot(folder/'operational.sqlite', config.history_end))
            cases.append((family, seed, folder))
    method, forecast_report = select_method(states)
    write_new(output/'forecast-selection.json', dict(method=method, report=forecast_report, sources=sources()))
    print(f'Built {len(cases)} development cases; selected forecast {method}', flush=True)
    runs, totals = [], {}
    for cover in (0, 3, 7):
        settings = PlannerSettings(forecast_method=method, safety_workdays=cover)
        rows = []
        for family, seed, folder in cases:
            row = run_policy(folder, settings, 'baseline')
            row.update(family=family, seed=seed)
            if row['audit_errors']:
                raise AssertionError(row['audit_errors'])
            write_new(output/f'baseline-{cover}-{family}-{seed}.json', row)
            rows.append(row)
            print(f'Baseline cover {cover}: {family}/{seed}: service {row["settled"]["service"]:.3f}', flush=True)
        totals[cover] = dict(service=sum(r['settled']['service'] for r in rows)/len(rows),
                            investment_cents=sum(r['settled']['investment_cents'] for r in rows)/len(rows))
        runs.extend(rows)
    best_service = max(t['service'] for t in totals.values())
    eligible = [c for c, t in totals.items() if t['service'] >= best_service-0.01]
    cover = min(eligible, key=lambda c: (totals[c]['investment_cents'], c))
    settings = PlannerSettings(forecast_method=method, safety_workdays=cover)
    write_new(output/'baseline-selection.json', dict(settings=asdict(settings), summaries=totals,
        rule='Lowest average investment among safety covers within one service percentage point of the best; equal case weights',
        reserved_generated=False, sources=sources()))
    if baseline_only:
        return
    for family, seed, folder in cases:
        row = run_policy(folder, settings, 'optimiser')
        row.update(family=family, seed=seed)
        write_new(output/f'optimiser-{family}-{seed}.json', row)
        print(f'Optimiser {family}/{seed}: {row["settled"]["service"]:.3f}; errors={row["audit_errors"]}', flush=True)


def main() -> None:
    """Run development evaluation only; no implicit reserved-seed access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['development'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-only', action='store_true')
    args = parser.parse_args()
    development(args.output, baseline_only=args.baseline_only)


if __name__ == '__main__':
    main()
