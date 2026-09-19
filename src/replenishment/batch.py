"""Bounded process-based evaluation; no shared policy state between scenarios."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
from time import monotonic

from src.demo_data.config import DEVELOPMENT_SEEDS, SCENARIO_FAMILIES
from .cli import write_new
from .contracts import PlannerSettings
from .evaluator import run_policy
from .scenarios import frozen_identity


def worker(folder: str, settings: dict, family: str, seed: int) -> dict:
    """Run one declared development case in an isolated Python process."""
    started = monotonic()
    result = run_policy(Path(folder), PlannerSettings(**settings), 'optimiser')
    result.update(family=family, seed=seed, elapsed_seconds=monotonic()-started)
    return result


def run_development(folder: Path, workers: int = 4) -> None:
    """Complete all development optimiser cases before any reserved evaluation."""
    selection = json.loads((folder/'baseline-selection.json').read_text())
    settings = selection['settings']
    output = folder/'optimiser'
    output.mkdir(exist_ok=False)
    identity = frozen_identity()
    write_new(output/'run-contract.json', dict(sources=identity, settings=settings, workers=workers,
                                             families=SCENARIO_FAMILIES, seeds=DEVELOPMENT_SEEDS))
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, str(folder/'work'/f'{family}-{seed}'), settings, family, seed): (family, seed)
                   for family in SCENARIO_FAMILIES for seed in DEVELOPMENT_SEEDS}
        for future in as_completed(futures):
            family, seed = futures[future]
            result = future.result()
            if frozen_identity() != identity:
                raise RuntimeError('Numerical source changed during development evaluation')
            write_new(output/f'{family}-{seed}.json', result)
            baseline = json.loads((folder/f'baseline-{settings["safety_workdays"]}-{family}-{seed}.json').read_text())
            a, b = result['settled'], baseline['settled']
            summary = dict(family=family, seed=seed, audit_errors=result['audit_errors'],
                           service_change_points=100*(a['service']-b['service']),
                           investment_change_fraction=a['investment_cents']/b['investment_cents']-1,
                           baseline=b, optimiser=a, elapsed_seconds=result['elapsed_seconds'])
            rows.append(summary)
            print(f'{family}/{seed}: service {summary["service_change_points"]:+.2f} points; '
                  f'investment {summary["investment_change_fraction"]:+.1%}; errors={result["audit_errors"]}', flush=True)
    rows.sort(key=lambda r: (r['family'], r['seed']))
    write_new(output/'summary.json', dict(cases=rows, sources=identity, reserved_generated=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    run_development(args.development, args.workers)
