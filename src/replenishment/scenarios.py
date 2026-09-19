"""Private evaluation materialisation using the unchanged v2 business recipe."""
from datetime import date
import hashlib
import json
from pathlib import Path

from src.demo_data.audit import audit_scenario
from src.demo_data.catalog import insert_master_data
from src.demo_data.config import DEVELOPMENT_SEEDS, EVALUATION_SEEDS, DemoConfig
from src.demo_data.engine import HistoryEngine
from src.demo_data.external import generate_requests, write_future_events
from src.demo_data.schema import create_database, OPERATIONAL_SCHEMA, EVALUATOR_SCHEMA
from src.demo_data.storage import validate_output


def frozen_identity() -> dict:
    """Freeze numerical code and the approved acceptance contract."""
    files = [Path('requirements.txt'), Path('docs/DISTRIBUTOR_IMPLEMENTATION_PLAN.md')]
    files += sorted(Path('src/demo_data').glob('*.py')) + sorted(Path('src/replenishment').glob('*.py'))
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def verify_freeze(path: Path) -> dict:
    """Reserved data are inaccessible until all declared development cases finish."""
    freeze = json.loads(path.read_text())
    if freeze.get('sources') != frozen_identity():
        raise ValueError('Frozen implementation or acceptance contract changed')
    if freeze.get('development_case_count') != 18 or not freeze.get('development_audits_passed'):
        raise ValueError('All 18 development cases must be audited before reserved generation')
    return freeze


def materialise(config: DemoConfig, output: Path, *, freeze_path: Path | None = None) -> dict:
    """Reproduce v2 records without weakening the original generator's seed guard."""
    config.validate()
    if config.seed not in DEVELOPMENT_SEEDS:
        if config.seed not in EVALUATION_SEEDS or freeze_path is None:
            raise ValueError('Reserved generation requires a frozen evaluation contract')
        verify_freeze(freeze_path)
    output = validate_output(output)
    output.mkdir(parents=True, exist_ok=False)
    op = create_database(output/'operational.sqlite', OPERATIONAL_SCHEMA)
    ev = create_database(output/'evaluator.sqlite', EVALUATOR_SCHEMA)
    try:
        catalog = insert_master_data(op, config)
        requests = generate_requests(config, catalog, date.fromisoformat(config.history_start), config.history_end, 'history')
        engine = HistoryEngine(op, config, catalog)
        engine.run(requests)
        future = generate_requests(config, catalog, config.future_start, config.future_end, 'future')
        write_future_events(ev, config, catalog, future)
        ev.executemany('INSERT INTO continuation_notices VALUES (?,?,?,?,?,?,?,?)', engine.pending_notices)
        ev.executemany('INSERT INTO continuation_deliveries VALUES (?,?,?,?,?,?,?)', [
            (i, d['line_id'], d['product_id'], d['po_id'], str(d['date']), d['units'], str(d['expiry']))
            for i, d in enumerate(engine.pending_deliveries, 1)])
        ev.executemany('INSERT INTO evaluator_manifest VALUES (?,?)', [
            ('schema_version', config.schema_version), ('synthetic_label', config.synthetic_label),
            ('scenario_family', config.scenario_family), ('seed', str(config.seed)), ('config_identity', config.identity())])
        op.executemany('INSERT INTO dataset_manifest VALUES (?,?)', [
            ('schema_version', config.schema_version), ('synthetic_label', config.synthetic_label),
            ('scenario_family', config.scenario_family), ('history_start', config.history_start),
            ('history_end', str(config.history_end)), ('future_start', str(config.future_start))])
        op.commit(); ev.commit()
    finally:
        op.close(); ev.close()
    audit = audit_scenario(output/'operational.sqlite', output/'evaluator.sqlite')
    if not audit['passed']:
        raise ValueError('Materialised business history failed its independent v2 audit')
    return audit
