"""Build reproducible operational and evaluator databases."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
import shutil

from .audit import audit_scenario, write_audit
from .catalog import insert_master_data
from .config import DEVELOPMENT_SEEDS, EVALUATION_SEEDS, SCENARIO_FAMILIES, DemoConfig, default_config, write_config
from .engine import HistoryEngine
from .external import generate_requests, write_future_events
from .reports import write_assumptions, write_coverage, write_walkthrough
from .schema import EVALUATOR_SCHEMA, OPERATIONAL_SCHEMA, create_database
from .storage import validate_output


def file_hash(path: Path) -> str:
    """Return a streaming SHA-256 hash."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_scenario(config: DemoConfig, output_dir: Path) -> dict:
    """Generate one scenario and its compact evidence, refusing replacement."""
    config.validate()
    if config.seed not in DEVELOPMENT_SEEDS:
        raise ValueError("Reserved evaluation seeds cannot be generated during database development")
    output_dir = validate_output(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing scenario directory: {output_dir}")
    output_dir.mkdir(parents=True)
    operational_path = output_dir / "operational.sqlite"
    evaluator_path = output_dir / "evaluator.sqlite"
    operational = evaluator = None
    try:
        operational = create_database(operational_path, OPERATIONAL_SCHEMA)
        catalog = insert_master_data(operational, config)
        historical_requests = generate_requests(
            config, catalog, date.fromisoformat(config.history_start), config.history_end, "history"
        )
        engine = HistoryEngine(operational, config, catalog)
        engine.run(historical_requests)
        operational.commit()

        evaluator = create_database(evaluator_path, EVALUATOR_SCHEMA)
        future_requests = generate_requests(config, catalog, config.future_start, config.future_end, "future")
        write_future_events(evaluator, config, catalog, future_requests)
        evaluator.executemany("INSERT INTO continuation_notices VALUES (?,?,?,?,?,?,?,?)", engine.pending_notices)
        evaluator.executemany("INSERT INTO continuation_deliveries VALUES (?,?,?,?,?,?,?)", [
            (i, item["line_id"], item["product_id"], item["po_id"], item["date"].isoformat(),
             item["units"], item["expiry"].isoformat())
            for i, item in enumerate(engine.pending_deliveries, 1)
        ])
        evaluator.executemany(
            "INSERT INTO evaluator_manifest VALUES (?,?)",
            (
                ("schema_version", config.schema_version),
                ("synthetic_label", config.synthetic_label),
                ("scenario_family", config.scenario_family),
                ("seed", str(config.seed)),
                ("config_identity", config.identity()),
            ),
        )
        evaluator.commit()
        evaluator.close()

        operational.executemany(
            "INSERT INTO dataset_manifest VALUES (?,?)",
            (
                ("schema_version", config.schema_version),
                ("synthetic_label", config.synthetic_label),
                ("scenario_family", config.scenario_family),
                ("history_start", config.history_start),
                ("history_end", config.history_end.isoformat()),
                ("future_start", config.future_start.isoformat()),
            ),
        )
        operational.commit()
        operational.close()

        write_config(config, output_dir / "regeneration_config.json")
        write_assumptions(output_dir / "assumption_register.json")
        audit = audit_scenario(operational_path, evaluator_path)
        write_audit(audit, output_dir / "audit.json")
        write_coverage(audit, config, output_dir / "coverage.md")
        write_walkthrough(operational_path, config, output_dir / "walkthrough.md")
        manifest = {
            "synthetic_label": config.synthetic_label,
            "schema_version": config.schema_version,
            "config_identity": config.identity(),
            "source_files": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
            "files": {
                path.name: {"sha256": file_hash(path), "bytes": path.stat().st_size}
                for path in sorted(output_dir.iterdir()) if path.is_file()
            },
        }
        (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        if not audit["passed"]:
            raise RuntimeError(f"Generated scenario failed audit: {output_dir / 'audit.json'}")
        return audit
    except Exception:
        # Preserve failed evidence for diagnosis; never discard an unfavourable run.
        raise
    finally:
        if operational is not None:
            operational.close()
        if evaluator is not None:
            evaluator.close()


def build_development_suite(output_dir: Path) -> dict:
    """Validate all 18 declared development scenarios and retain compact evidence."""
    output_dir = validate_output(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite suite directory: {output_dir}")
    output_dir.mkdir(parents=True)
    work_dir = output_dir / ".suite-work"
    rows = []
    try:
        work_dir.mkdir()
        for family in SCENARIO_FAMILIES:
            for seed in DEVELOPMENT_SEEDS:
                scenario_dir = work_dir / f"{family}-{seed}"
                report = generate_scenario(default_config(family, seed), scenario_dir)
                rows.append(
                    {
                        "scenario_family": family,
                        "seed": seed,
                        "passed": report["passed"],
                        "checks": report["checks"],
                        "config": default_config(family, seed).public_dict(),
                        "operational_sha256": file_hash(scenario_dir / "operational.sqlite"),
                        "evaluator_sha256": file_hash(scenario_dir / "evaluator.sqlite"),
                        **report["coverage"],
                    }
                )
                shutil.rmtree(scenario_dir)
        suite = {
            "synthetic_label": default_config().synthetic_label,
            "scenario_count": len(rows),
            "all_passed": all(row["passed"] for row in rows),
            "evaluation_seeds_generated": False,
            "source_files": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
            "scenarios": rows,
        }
        (output_dir / "suite_report.json").write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n")
        (output_dir / "suite_config.json").write_text(
            json.dumps({"families": SCENARIO_FAMILIES, "development_seeds": DEVELOPMENT_SEEDS, "evaluation_seeds_reserved": EVALUATION_SEEDS}, indent=2) + "\n"
        )
        shutil.rmtree(work_dir)
        return suite
    except Exception:
        # Retain diagnostic files when a scenario fails.
        raise
