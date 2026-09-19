"""Behaviour and integrity tests for the synthetic distributor database."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from datetime import date, timedelta

import pytest

from src.demo_data.audit import audit_scenario
from src.demo_data.config import EVALUATION_SEEDS, default_config
from src.demo_data.generator import file_hash, generate_scenario
from src.demo_data.schema import OPERATIONAL_SCHEMA, create_database, connect
from src.demo_data.snapshot import export_csv, snapshot
from src.demo_data.utils import stable_fraction
from src.demo_data.external import supply_condition


TEST_ROOT = Path(__file__).resolve().parent.parent / "artifacts" / "distributor-demo" / ".test-work"


@pytest.fixture(scope="module")
def scenario_paths():
    shutil.rmtree(TEST_ROOT, ignore_errors=True)
    scenario = TEST_ROOT / "scenario"
    generate_scenario(default_config("supplier_disruption", 2202), scenario)
    yield scenario / "operational.sqlite", scenario / "evaluator.sqlite"
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


def test_generated_database_passes_all_required_audits(scenario_paths):
    report = audit_scenario(*scenario_paths)
    assert report["passed"]
    assert all(check["failure_count"] == 0 for check in report["checks"])


def test_generated_scope_and_synthetic_label_are_explicit(scenario_paths):
    operational, evaluator = scenario_paths
    db = connect(operational)
    assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 30
    assert db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 4
    assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 20
    label = db.execute("SELECT value FROM dataset_manifest WHERE key='synthetic_label'").fetchone()[0]
    assert label.startswith("SYNTHETIC DEMONSTRATION DATA")
    assert "seed" not in {row[0] for row in db.execute("SELECT key FROM dataset_manifest")}
    db.close()
    hidden = connect(evaluator)
    assert hidden.execute("SELECT COUNT(*) FROM future_customer_orders").fetchone()[0] > 0
    hidden.close()


def test_as_of_snapshot_never_includes_later_known_records(scenario_paths):
    operational, _ = scenario_paths
    cutoff = "2025-03-03"
    result = snapshot(operational, cutoff)
    for table, rows in result.items():
        if table not in {"snapshot_stock", "snapshot_manifest"}:
            assert all(row["known_at"] <= cutoff for row in rows)


def test_changing_evaluator_future_cannot_change_operational_snapshot(scenario_paths):
    operational, evaluator_path = scenario_paths
    before = snapshot(operational, "2025-07-06")
    evaluator = connect(evaluator_path)
    evaluator.execute("UPDATE future_customer_order_lines SET requested_units=requested_units+999 WHERE rowid=1")
    evaluator.commit()
    evaluator.close()
    after = snapshot(operational, "2025-07-06")
    assert before == after


def test_csv_export_matches_restricted_snapshot(scenario_paths):
    operational, _ = scenario_paths
    output = TEST_ROOT / "export"
    files = export_csv(operational, output, "2025-03-03")
    assert {path.name for path in files} >= {"products.csv", "snapshot_stock.csv", "snapshot_manifest.csv"}
    assert "SYNTHETIC DEMONSTRATION DATA" in (output / "snapshot_manifest.csv").read_text()
    with (output / "customer_orders.csv").open() as handle:
        assert "2025-04" not in handle.read()


def test_same_configuration_reproduces_identical_databases():
    first = TEST_ROOT / "repeat-a"
    second = TEST_ROOT / "repeat-b"
    config = default_config("ordinary", 3303)
    generate_scenario(config, first)
    generate_scenario(config, second)
    assert file_hash(first / "operational.sqlite") == file_hash(second / "operational.sqlite")
    assert file_hash(first / "evaluator.sqlite") == file_hash(second / "evaluator.sqlite")


def test_supplier_conditions_do_not_depend_on_random_call_order():
    keys = ["PO-00001", "PO-00002", "PO-00003"]
    forward = {key: stable_fraction(1101, f"history-supply:{key}") for key in keys}
    reverse = {key: stable_fraction(1101, f"history-supply:{key}") for key in reversed(keys)}
    assert forward == reverse


def test_one_lot_hand_reconciles_through_the_event_sequence(scenario_paths):
    operational, _ = scenario_paths
    db = connect(operational)
    row = db.execute(
        """
        SELECT l.lot_id, c.closing_units,
               SUM(CASE WHEN m.movement_type IN ('opening','receipt') THEN m.quantity_delta_units ELSE 0 END) supplied,
               -SUM(CASE WHEN m.movement_type='shipment' THEN m.quantity_delta_units ELSE 0 END) shipped,
               -SUM(CASE WHEN m.movement_type='expiry' THEN m.quantity_delta_units ELSE 0 END) expired
        FROM stock_lots l JOIN stock_movements m USING(lot_id) JOIN closing_stock c USING(lot_id)
        GROUP BY l.lot_id HAVING COUNT(*) > 1 ORDER BY l.lot_id LIMIT 1
        """
    ).fetchone()
    assert row["supplied"] - row["shipped"] - row["expired"] == row["closing_units"]
    db.close()


def test_invalid_input_fixtures_are_rejected_by_schema():
    invalid = TEST_ROOT / "invalid.sqlite"
    db = create_database(invalid, OPERATIONAL_SCHEMA)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)", ("P", "P", "C", "case", 12, 100, 90, "2025-01-01", "2025-01-01"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO suppliers VALUES (?,?,?,?,?,?,?,?)", ("S", "S", 0, 0, 0, 2, "2025-01-01", "2025-01-01"))
        db.execute("INSERT INTO suppliers VALUES (?,?,?,?,?,?,?,?)", ("S", "S2", 0, 0, 0, 2, "2025-01-01", "2025-01-01"))
    db.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)", ("P", "P", "C", "each", 12, 100, 90, "2025-01-01", "2025-01-01"))
    with pytest.raises(sqlite3.IntegrityError, match="NOT NULL"):
        db.execute("INSERT INTO supplier_product_terms VALUES (?,?,?,?,?,?,?,?,?)", ("T", "S", "P", None, 12, "2025-01-01", None, "2025-01-01", "2025-01-01"))
    db.close()


def test_reserved_evaluation_seeds_cannot_be_generated():
    config = replace(default_config(), seed=EVALUATION_SEEDS[0])
    with pytest.raises(ValueError, match="Reserved evaluation seeds"):
        generate_scenario(config, TEST_ROOT / "reserved")


def test_existing_output_is_never_overwritten(scenario_paths):
    with pytest.raises(FileExistsError):
        generate_scenario(default_config(), scenario_paths[0].parent)


def test_opening_snapshot_status_is_not_final_history_status(scenario_paths):
    early = snapshot(scenario_paths[0], "2025-01-06")
    arrivals = {r["supplier_order_line_id"] for r in early["receipts"]}
    for line in early["supplier_order_lines"]:
        if line["supplier_order_line_id"] not in arrivals:
            assert line["received_units"] == 0
            assert line["outstanding_units"] == line["ordered_units"]
    later = snapshot(scenario_paths[0], "2025-07-06")
    assert any(r["status"] == "received" for r in later["supplier_orders"])
    assert all(r["status"] != "received" for r in early["supplier_orders"] if
               not any(l["supplier_order_id"] == r["supplier_order_id"] and l["received_units"] for l in early["supplier_order_lines"]))


def test_mutating_later_operational_receipts_cannot_change_early_snapshot(scenario_paths):
    copy = TEST_ROOT / "later-receipts.sqlite"
    shutil.copy2(scenario_paths[0], copy)
    before = snapshot(copy, "2025-02-03")
    with connect(copy) as db:
        db.execute("UPDATE receipts SET received_units=received_units+999 WHERE received_date>'2025-03-01'")
        db.execute("UPDATE supplier_orders SET status='invented_future_state'")
    assert snapshot(copy, "2025-02-03") == before


def test_partial_receipts_sum_once_when_deriving_order_status(scenario_paths):
    snap = snapshot(scenario_paths[0], "2025-07-06")
    counts = {}
    for r in snap["receipts"]:
        key = r["supplier_order_line_id"]
        counts[key] = counts.get(key, 0) + 1
    completed_split_lines = [l for l in snap["supplier_order_lines"] if counts.get(l["supplier_order_line_id"], 0) > 1 and not l["outstanding_units"]]
    assert completed_split_lines
    for line in completed_split_lines:
        sibling_lines = [l for l in snap["supplier_order_lines"] if l["supplier_order_id"] == line["supplier_order_id"]]
        if all(l["outstanding_units"] == 0 for l in sibling_lines):
            assert next(o for o in snap["supplier_orders"] if o["supplier_order_id"] == line["supplier_order_id"])["status"] == "received"


def test_snapshot_hides_generator_labels_and_future_regime(scenario_paths):
    snap = snapshot(scenario_paths[0], "2025-07-06")
    assert all("demand_class" not in p for p in snap["products"])
    assert all("demand_multiplier_basis_points" not in p for p in snap["promotions"])
    assert "scenario_family" not in snap["snapshot_manifest"][0]


def test_readonly_and_out_of_interval_requests_do_not_create_files(scenario_paths):
    missing = TEST_ROOT / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        snapshot(missing, "2025-01-06")
    assert not missing.exists()
    with pytest.raises(ValueError, match="interval"):
        snapshot(scenario_paths[0], "2025-07-07")
    with pytest.raises(ValueError, match="subdirectory"):
        export_csv(scenario_paths[0], Path("data/outside-demo"), "2025-01-06")
    assert not Path("data/outside-demo").exists()


@pytest.mark.parametrize("damage,expected", [
    ("DELETE FROM closing_stock WHERE lot_id=(SELECT lot_id FROM closing_stock LIMIT 1)", "independent_fefo_expiry_and_complete_closing_ledger"),
    ("DELETE FROM stock_movements WHERE movement_type='shipment' AND rowid=(SELECT rowid FROM stock_movements WHERE movement_type='shipment' LIMIT 1)", "source_records_match_physical_movements"),
    ("UPDATE supplier_updates SET known_at='2026-01-01' WHERE rowid=1", "no_unreleased_future_operational_events"),
    ("UPDATE shipments SET shipped_units=shipped_units+1 WHERE rowid=1", "source_records_match_physical_movements"),
])
def test_audit_detects_corruption_instead_of_only_matching_totals(scenario_paths, damage, expected):
    copy = TEST_ROOT / "damaged.sqlite"
    shutil.copy2(scenario_paths[0], copy)
    with connect(copy) as db:
        db.execute(damage)
    report = audit_scenario(copy)
    assert not report["passed"]
    assert not next(c for c in report["checks"] if c["check"] == expected)["passed"]


def test_supply_response_is_supplier_date_keyed():
    config = default_config()
    dates = [date(2025, 7, 7), date(2025, 7, 8)]
    assert [supply_condition(config, "SUP-01", d) for d in dates] == [(3, 6500), (3, 6500)]
    assert {d: supply_condition(config, "SUP-03", d) for d in dates} == {
        d: supply_condition(config, "SUP-03", d) for d in reversed(dates)}


def test_empty_exports_keep_headers(scenario_paths):
    paths = export_csv(scenario_paths[0], TEST_ROOT / "empty-export", "2025-01-06")
    assert next(p for p in paths if p.name == "cancellations.csv").read_text().startswith("cancellation_id,")


def test_hand_calculated_partial_whole_line_and_expiry_sequence():
    from src.demo_data.catalog import insert_master_data
    from src.demo_data.engine import HistoryEngine
    config = default_config()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(OPERATIONAL_SCHEMA)
    catalog = insert_master_data(db, config)
    product = catalog["products"][0]
    for c in catalog["customers"]:
        c.update(minimum_remaining_shelf_life_days=0, maximum_late_workdays=0)
    catalog["customers"][0]["accepts_partial"] = 1
    catalog["customers"][1]["accepts_partial"] = 0
    # Dispatch helper fixture uses zero freshness to expose expiry the next day;
    # generated business terms still require 14/30/60 days.
    engine = HistoryEngine(db, config, catalog)
    day = date(2025, 1, 6)
    engine.lots["HAND"] = dict(lot_id="HAND", product_id=product["product_id"], received_date=day,
                               expiry_date=day+timedelta(days=1), cost=100, remaining=10)
    db.execute("INSERT INTO stock_lots VALUES (?,?,?,?,?,?,?,?,?)", ("HAND", product["product_id"], None,
               str(day), str(day+timedelta(days=1)), 100, 10, str(day), str(day)))
    engine._movement("HAND", "opening", 10, "HAND", day)
    requests = [dict(customer_order_id=f"HAND-{i}", customer_id=cid, created_date=day, due_date=day,
                     lines=[dict(product_id=product["product_id"], requested_units=qty)])
                for i, (cid, qty) in enumerate([("CUS-001", 4), ("CUS-002", 7), ("CUS-001", 4)])]
    engine._record_requests(day, requests)
    engine._dispatch(day)
    engine._cancel_overdue(day)
    assert engine.lots["HAND"]["remaining"] == 2
    assert db.execute("SELECT SUM(shipped_units) FROM shipments").fetchone()[0] == 8
    assert db.execute("SELECT SUM(cancelled_units) FROM cancellations").fetchone()[0] == 7
    engine._expire(day+timedelta(days=1))
    assert engine.lots["HAND"]["remaining"] == 0
    assert db.execute("SELECT quantity_delta_units FROM stock_movements WHERE movement_type='expiry'").fetchone()[0] == -2
    db.close()


def test_capacity_rejection_preserves_retry_quantity_and_expiry():
    from src.demo_data.catalog import insert_master_data
    from src.demo_data.engine import HistoryEngine
    config = replace(default_config(), warehouse_capacity_millilitres=1)
    db = sqlite3.connect(":memory:"); db.row_factory = sqlite3.Row
    db.executescript(OPERATIONAL_SCHEMA)
    catalog = insert_master_data(db, config)
    engine = HistoryEngine(db, config, catalog)
    day = date(2025, 1, 6)
    product = catalog["products"][0]
    engine._create_po(catalog["suppliers"][0], [(product, product["minimum_order_units"])], day, day)
    before = engine._pending_product_units(product["product_id"])
    original_expiry = engine.pending_deliveries[0]["expiry"]
    engine._receive(day)
    assert engine._pending_product_units(product["product_id"]) == before
    assert sum(d["units"] for d in engine.pending_deliveries) == before
    assert all(d["expiry"] == original_expiry for d in engine.pending_deliveries)
    assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 0
    db.close()


def test_before_ordering_snapshot_excludes_same_day_shipments_and_orders(scenario_paths):
    day = "2025-04-07"
    early = snapshot(scenario_paths[0], day, phase="before_ordering")
    late = snapshot(scenario_paths[0], day)
    for table in ("supplier_orders", "supplier_order_lines", "shipments", "cancellations"):
        assert all(r["known_at"] < day for r in early[table])
    same_day_units = sum(r["shipped_units"] for r in late["shipments"] if r["dispatch_date"] == day)
    assert same_day_units > 0
    assert sum(r["quantity_units"] for r in early["snapshot_stock"]) - sum(r["quantity_units"] for r in late["snapshot_stock"]) == same_day_units


def test_regeneration_with_different_future_requests_preserves_entire_operational_db(monkeypatch):
    from src.demo_data import generator
    original = generator.generate_requests
    first, second = TEST_ROOT / "future-a", TEST_ROOT / "future-b"
    config = default_config("demand_changes", 1101)
    generator.generate_scenario(config, first)
    def altered(*args):
        requests = original(*args)
        if args[-1] == "future":
            for r in requests:
                for line in r["lines"]:
                    line["requested_units"] += 100
        return requests
    monkeypatch.setattr(generator, "generate_requests", altered)
    generator.generate_scenario(config, second)
    assert file_hash(first / "operational.sqlite") == file_hash(second / "operational.sqlite")
    assert file_hash(first / "evaluator.sqlite") != file_hash(second / "evaluator.sqlite")


def test_evaluator_continuation_accounts_for_every_pending_historical_unit(scenario_paths):
    report = audit_scenario(*scenario_paths)
    assert next(c for c in report["checks"] if c["check"] == "evaluator_references_and_open_orders_continue")["passed"]
    copy = TEST_ROOT / "missing-continuation.sqlite"
    shutil.copy2(scenario_paths[1], copy)
    with connect(copy) as db:
        db.execute("DELETE FROM continuation_deliveries")
    assert not audit_scenario(scenario_paths[0], copy)["passed"]


def test_strict_schema_rejects_fractional_stock(scenario_paths):
    copy = TEST_ROOT / "fractional.sqlite"
    shutil.copy2(scenario_paths[0], copy)
    with connect(copy) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE closing_stock SET closing_units=1.5 WHERE rowid=1")
