"""Reproduce saved actions and disclose carry-in obligations separately.

This is a post-run reporting audit. It does not call or change the optimiser,
alter the frozen primary cohort, or select cases based on their outcomes.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

from src.demo_data.utils import date_range
from src.demo_data.schema import connect
from src.demo_data.storage import validate_output
from src.replenishment.cli import write_new
from src.replenishment.contracts import PlannerSettings, PlanRequest, Purchase
from src.replenishment.evaluator import World
from src.replenishment.physical import Operations
from src.replenishment.projection import metrics
from src.replenishment.scenarios import verify_freeze
from src.replenishment.state import load_snapshot


def replay_saved(folder: Path, result: dict, sensitivity: str) -> dict:
    """Reconstruct a saved policy without solving again or changing any actions."""
    with connect(folder/'operational.sqlite', readonly=True) as db:
        manifest = dict(db.execute('SELECT key, value FROM dataset_manifest'))
    anchor = date.fromisoformat(manifest['history_end'])
    start, end = anchor+timedelta(days=1), anchor+timedelta(weeks=8)
    initial = load_snapshot(folder/'operational.sqlite', anchor)
    carry_in = {key: line for key, line in initial.demand.items() if line.remaining}
    op = Operations(initial)
    world = World(folder, delay_days=2 if sensitivity == 'delay' else 0,
                  freshness_days=30 if sensitivity == 'freshness' else None)
    decisions = {d['day']: d for d in result['decisions']}
    if len(decisions) != len(result['decisions']):
        raise ValueError('Duplicate decision dates in saved report')
    settings = PlannerSettings(**result['settings'])
    hashes = {}
    for day in date_range(start, end+timedelta(days=30)):
        op.begin_day(day)
        if day.weekday() < 5:
            world.release(op)
        if str(day) in decisions:
            hashes[str(day)] = PlanRequest(op.state, settings).identity()
            purchases = [Purchase(date.fromisoformat(p['day']), p['supplier'], p['product'], p['units'])
                         for p in decisions[str(day)]['purchases']]
            for line in op.place(purchases):
                world.schedule(op, line)
        op.finish_day()
    reconstructed = metrics(op, start, end)
    if reconstructed != result['settled']:
        raise AssertionError('Replayed outcomes do not equal the saved frozen report')
    errors = op.audit()
    if errors:
        raise AssertionError(errors)
    carry_rows = []
    for key, original in carry_in.items():
        final = op.state.demand[key]
        carry_rows.append(dict(line=key, product=final.product, customer=final.customer,
            opening_unfulfilled=original.remaining,
            additionally_shipped=final.shipped-original.shipped,
            additionally_on_time=final.on_time-original.on_time,
            additionally_cancelled=final.cancelled-original.cancelled,
            still_open=final.remaining))
    for row in carry_rows:
        if row['opening_unfulfilled'] != row['additionally_shipped']+row['additionally_cancelled']+row['still_open']:
            raise AssertionError('Carry-in customer obligation does not reconcile')
    return dict(outcomes_reproduced=True, audit_errors=errors, decision_input_hashes=hashes,
                carry_in=carry_rows,
                receipt_units=sum(m['quantity'] for m in op.movements if m['kind']=='receipt'),
                shipped_units=-sum(m['quantity'] for m in op.movements if m['kind']=='shipment'),
                expired_units=-sum(m['quantity'] for m in op.movements if m['kind']=='expiry'),
                source_database_hashes={name: hashlib.sha256((folder/name).read_bytes()).hexdigest()
                                      for name in ('operational.sqlite', 'evaluator.sqlite')})


def audit_results(root: Path) -> dict:
    """Audit every completed sensitivity case; primary gate values are unchanged."""
    root = validate_output(root)
    verify_freeze(root/'run-contract.json')
    output = root/'action-replay-audit'
    output.mkdir(exist_ok=False)
    summaries = []
    for sensitivity in ('nominal', 'delay', 'freshness'):
        stage = root/sensitivity
        if not stage.exists():
            continue
        for path in sorted(stage.glob('*.json')):
            row = json.loads(path.read_text())
            if 'baseline' not in row or 'optimiser' not in row:
                continue
            folder = root/'work'/f'{row["family"]}-{row["seed"]}'
            reports = {method: replay_saved(folder, row[method], sensitivity) for method in ('baseline', 'optimiser')}
            write_new(output/f'{sensitivity}-{row["family"]}-{row["seed"]}.json', reports)
            totals = {method: {key: sum(r[key] for r in report['carry_in'])
                              for key in ('opening_unfulfilled', 'additionally_shipped', 'additionally_on_time',
                                          'additionally_cancelled', 'still_open')}
                      for method, report in reports.items()}
            summaries.append(dict(family=row['family'], seed=row['seed'], sensitivity=sensitivity,
                                  outcomes_reproduced=True, carry_in=totals))
    summary = dict(cases=summaries, audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        primary_cohort='Customer requests created during the eight evaluation weeks; unchanged from frozen evaluation',
        additional_diagnostic='Carry-in requests reported separately; this audit does not change the release gate')
    write_new(output/'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    result = audit_results(parser.parse_args().root)
    print(f'Reproduced {len(result["cases"])} paired case reports and reconciled carry-in requests.')
