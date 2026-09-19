"""Resume bounded development batches without replacing evidence or changing code."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
from time import monotonic

from src.demo_data.config import DEVELOPMENT_SEEDS, SCENARIO_FAMILIES, default_config
from src.demo_data.generator import generate_scenario
from src.demo_data.storage import validate_output
from src.replenishment.cli import write_new
from src.replenishment.contracts import PlannerSettings
from src.replenishment.evaluator import run_policy
from .checkpoints import exclusive_batch, archive_sources


def identity() -> dict[str, str]:
    """Cover numerical code, tests and the iteration protocol, not changing reports."""
    paths = list(Path('src').rglob('*.py')) + list(Path('tests').glob('*.py'))
    paths += [Path('requirements.txt'), Path('pytest.ini'), Path('docs/DISTRIBUTOR_ITERATION_PROTOCOL.md')]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def run_case(root: str, family: str, seed: int, settings: dict) -> dict:
    """Run the same immutable scenario independently for both methods."""
    started = monotonic()
    root = Path(root)
    folder = root/'work'/f'{family}-{seed}'
    config = default_config(family, seed)
    if not folder.exists():
        generate_scenario(config, folder)
    # Interrupted cases may reuse a database only after its retained hashes match.
    manifest = json.loads((folder/'run_manifest.json').read_text())
    for name, info in manifest['files'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError(f'Interrupted input changed: {folder/name}')
    result = dict(family=family, seed=seed, configuration=config.public_dict(), input_manifest=manifest)
    for method in ('baseline', 'optimiser'):
        result[method] = run_policy(folder, PlannerSettings(**settings), method)
        if result[method]['audit_errors']:
            raise ValueError(f'{family}/{seed}/{method}: accounting failure')
    result['elapsed_seconds'] = monotonic()-started
    return result


def summarise(rows: list[dict]) -> dict:
    """Report every outcome; development success never authorises a sales claim."""
    cases = []
    for row in sorted(rows, key=lambda r: (r['family'], r['seed'])):
        a, b = row['optimiser']['settled'], row['baseline']['settled']
        service = 100*(a['service']-b['service'])
        capital = a['investment_cents']/b['investment_cents']-1 if b['investment_cents'] else None
        tail = all(a[k] <= b[k]+max(.05*b[k], 2500)
                   for k in ('expiry_cents', 'ending_investment_cents'))
        route = (service >= 2-1e-7 and a['investment_cents'] <= 1.05*b['investment_cents']) or (
            b['investment_cents'] > 0 and capital <= -.1+1e-9 and service >= -1-1e-7)
        cases.append(dict(family=row['family'], seed=row['seed'], service_change_points=service,
            investment_change_fraction=capital, improvement_route=bool(route and tail), tail_ok=tail,
            complete_line_change_points=100*(a['complete_line_service']-b['complete_line_service'])))
    return dict(cases=cases, development_only=True, permits_release_claim=False,
        severe_regressions=[r for r in cases if r['service_change_points'] < -5-1e-7])


def _run_locked(root: Path, hypothesis: str, workers: int) -> None:
    """Create or resume exactly one declared batch; refuse changed source/settings."""
    root = validate_output(root)
    root.mkdir(parents=True, exist_ok=True)
    settings = asdict(PlannerSettings(forecast_method='mean8', safety_workdays=0))
    contract = dict(sources=identity(), hypothesis=hypothesis, settings=settings,
                    families=SCENARIO_FAMILIES, seeds=DEVELOPMENT_SEEDS, workers=workers)
    # JSON normalisation keeps tuple/list representations equal after restart.
    contract = json.loads(json.dumps(contract))
    target = root/'contract.json'
    if target.exists():
        if json.loads(target.read_text()) != contract:
            raise ValueError('Resume refused: source, hypothesis, settings or batch scope changed')
    else:
        write_new(target, contract)
    archive_sources(root, contract['sources'])
    (root/'work').mkdir(exist_ok=True)
    (root/'cases').mkdir(exist_ok=True)
    rows, pending = [], []
    for family in SCENARIO_FAMILIES:
        for seed in DEVELOPMENT_SEEDS:
            path = root/'cases'/f'{family}-{seed}.json'
            if path.exists():
                rows.append(json.loads(path.read_text()))
            else:
                pending.append((family, seed))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_case, str(root), family, seed, settings) for family, seed in pending]
        for future in as_completed(futures):
            row = future.result()
            if identity() != contract['sources']:
                raise RuntimeError('Source changed during a batch; results cannot share this version')
            write_new(root/'cases'/f'{row["family"]}-{row["seed"]}.json', row)
            rows.append(row)
            # Original manifests/configs are in the result before removing copies.
            shutil.rmtree(root/'work'/f'{row["family"]}-{row["seed"]}')
            item = summarise([row])['cases'][0]
            print(f'{row["family"]}/{row["seed"]}: service {item["service_change_points"]:+.2f} points; '
                  f'capital {item["investment_change_fraction"]:+.1%}', flush=True)
    summary = summarise(rows)
    path = root/'summary.json'
    if not path.exists():
        write_new(path, summary)
    elif json.loads(path.read_text()) != summary:
        raise ValueError('Completed summary changed')
    print(f'Completed {len(rows)} development cases; fresh evaluation remains closed.', flush=True)


def run(root: Path, hypothesis: str, workers: int) -> None:
    """Own a batch exclusively, including restarts after interrupted processes."""
    root = validate_output(root)
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_batch(root):
        _run_locked(root, hypothesis, workers)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--hypothesis', required=True)
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    run(args.output, args.hypothesis, args.workers)
