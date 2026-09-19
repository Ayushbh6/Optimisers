"""Independent accounting and relationship checks for generated scenarios."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import json
from pathlib import Path

from .schema import connect
from .utils import add_workdays
from .integrity import detailed_checks, continuation_check


def _check(name: str, failures: list, details: dict | None = None) -> dict:
    return {"check": name, "passed": not failures, "failure_count": len(failures), "examples": failures[:5], "details": details or {}}


def audit_scenario(operational_path: Path, evaluator_path: Path | None = None) -> dict:
    """Audit one scenario without trusting generator in-memory state."""
    db = connect(operational_path, readonly=True)
    checks = []
    foreign_keys = [dict(row) for row in db.execute("PRAGMA foreign_key_check")]
    checks.append(_check("all_foreign_keys_resolve", foreign_keys))
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    checks.append(_check("sqlite_integrity", [] if integrity == "ok" else [{"result": integrity}]))

    lot_failures = []
    lot_rows = db.execute(
        """
        SELECT l.lot_id, COALESCE(SUM(m.quantity_delta_units),0) ledger_units, c.closing_units
        FROM stock_lots l JOIN closing_stock c USING(lot_id)
        LEFT JOIN stock_movements m USING(lot_id)
        GROUP BY l.lot_id
        """
    ).fetchall()
    for row in lot_rows:
        if row["ledger_units"] != row["closing_units"] or row["ledger_units"] < 0:
            lot_failures.append(dict(row))
    checks.append(_check("lot_stock_reconciles", lot_failures, {"lots_checked": len(lot_rows)}))

    negative_ledger = []
    for lot in db.execute("SELECT lot_id FROM stock_lots ORDER BY lot_id"):
        balance = 0
        movements = db.execute(
            "SELECT * FROM stock_movements WHERE lot_id=? ORDER BY event_date, movement_id",
            (lot["lot_id"],),
        ).fetchall()
        for movement in movements:
            balance += movement["quantity_delta_units"]
            if balance < 0:
                negative_ledger.append({"lot_id": lot["lot_id"], "movement_id": movement["movement_id"], "balance": balance})
    checks.append(_check("stock_never_negative", negative_ledger))

    customer_failures = []
    customer_rows = db.execute(
        """
        SELECT col.customer_order_line_id, col.requested_units,
               COALESCE((SELECT SUM(shipped_units) FROM shipments s WHERE s.customer_order_line_id=col.customer_order_line_id),0) shipped,
               COALESCE((SELECT SUM(cancelled_units) FROM cancellations c WHERE c.customer_order_line_id=col.customer_order_line_id),0) cancelled
        FROM customer_order_lines col
        """
    ).fetchall()
    for row in customer_rows:
        if row["shipped"] + row["cancelled"] > row["requested_units"]:
            customer_failures.append(dict(row))
    checks.append(_check("customer_quantities_reconcile", customer_failures, {"lines_checked": len(customer_rows)}))

    supplier_failures = []
    supplier_rows = db.execute(
        """
        SELECT sol.supplier_order_line_id, sol.ordered_units,
               COALESCE(SUM(r.received_units),0) received
        FROM supplier_order_lines sol LEFT JOIN receipts r USING(supplier_order_line_id)
        GROUP BY sol.supplier_order_line_id
        """
    ).fetchall()
    for row in supplier_rows:
        if row["received"] > row["ordered_units"]:
            supplier_failures.append(dict(row))
    checks.append(_check("supplier_quantities_reconcile", supplier_failures, {"lines_checked": len(supplier_rows)}))

    eligibility_failures = [dict(row) for row in db.execute(
        """
        SELECT s.shipment_id, s.dispatch_date, l.expiry_date,
               c.minimum_remaining_shelf_life_days
        FROM shipments s
        JOIN stock_lots l USING(lot_id)
        JOIN customer_order_lines col USING(customer_order_line_id)
        JOIN customer_orders co USING(customer_order_id)
        JOIN customers c USING(customer_id)
        WHERE julianday(l.expiry_date) - julianday(s.dispatch_date) < c.minimum_remaining_shelf_life_days
        """
    )]
    checks.append(_check("shipments_meet_expiry_terms", eligibility_failures))

    customer_rules = {row["customer_id"]: dict(row) for row in db.execute("SELECT * FROM customers")}
    partial_failures, lateness_failures = [], []
    for row in db.execute(
        """
        SELECT col.customer_order_line_id, co.customer_id, co.due_date, col.requested_units,
               COALESCE(SUM(s.shipped_units),0) shipped, MAX(s.dispatch_date) last_dispatch
        FROM customer_order_lines col JOIN customer_orders co USING(customer_order_id)
        LEFT JOIN shipments s USING(customer_order_line_id)
        GROUP BY col.customer_order_line_id
        """
    ):
        customer = customer_rules[row["customer_id"]]
        if not customer["accepts_partial"] and row["shipped"] not in (0, row["requested_units"]):
            partial_failures.append(dict(row))
        if row["last_dispatch"]:
            deadline = add_workdays(date.fromisoformat(row["due_date"]), customer["maximum_late_workdays"])
            if date.fromisoformat(row["last_dispatch"]) > deadline:
                lateness_failures.append(dict(row))
    checks.append(_check("customer_partial_rules_respected", partial_failures))
    checks.append(_check("customer_lateness_rules_respected", lateness_failures))

    order_failures = [dict(row) for row in db.execute(
        """
        SELECT sol.supplier_order_line_id, sol.ordered_units, p.case_size_units, t.minimum_order_units
        FROM supplier_order_lines sol JOIN products p USING(product_id)
        JOIN supplier_orders so USING(supplier_order_id)
        JOIN supplier_product_terms t ON t.product_id=sol.product_id AND t.supplier_id=so.supplier_id
        WHERE sol.ordered_units % p.case_size_units != 0 OR sol.ordered_units < t.minimum_order_units
        """
    )]
    checks.append(_check("supplier_case_and_product_minimums_respected", order_failures))

    minimum_failures = [dict(row) for row in db.execute(
        """
        SELECT so.supplier_order_id, s.minimum_order_value_cents,
               SUM(sol.ordered_units * sol.unit_cost_cents) merchandise_cents
        FROM supplier_orders so JOIN suppliers s USING(supplier_id)
        JOIN supplier_order_lines sol USING(supplier_order_id)
        GROUP BY so.supplier_order_id
        HAVING merchandise_cents < s.minimum_order_value_cents
        """
    )]
    checks.append(_check("supplier_order_minimums_respected", minimum_failures))

    budget = db.execute("SELECT weekly_new_order_budget_cents FROM planning_limits ORDER BY effective_from DESC LIMIT 1").fetchone()[0]
    history_start = date.fromisoformat(dict(db.execute("SELECT key, value FROM dataset_manifest").fetchall()).get("history_start", "9999-12-31"))
    weekly_spend = defaultdict(int)
    for row in db.execute(
        """
        SELECT so.supplier_order_id, so.placed_date, so.delivery_charge_cents,
               SUM(sol.ordered_units * sol.unit_cost_cents) merchandise_cents
        FROM supplier_orders so JOIN supplier_order_lines sol USING(supplier_order_id)
        GROUP BY so.supplier_order_id
        """
    ):
        placed = date.fromisoformat(row["placed_date"])
        if placed < history_start:
            continue
        week = placed.fromordinal(placed.toordinal() - placed.weekday()).isoformat()
        weekly_spend[week] += row["delivery_charge_cents"] + row["merchandise_cents"]
    budget_failures = [{"week_start": week, "spend_cents": spend, "budget_cents": budget} for week, spend in weekly_spend.items() if spend > budget]
    checks.append(_check("weekly_new_order_budget_respected", budget_failures, {"weeks_checked": len(weekly_spend)}))

    capacity = db.execute("SELECT warehouse_capacity_ml FROM planning_limits ORDER BY effective_from DESC LIMIT 1").fetchone()[0]
    lot_volume = {
        row["lot_id"]: row["storage_ml_per_unit"]
        for row in db.execute("SELECT l.lot_id, p.storage_ml_per_unit FROM stock_lots l JOIN products p USING(product_id)")
    }
    balances = defaultdict(int)
    used_ml = 0
    capacity_failures = []
    for movement in db.execute("SELECT * FROM stock_movements ORDER BY event_date, movement_id"):
        lot_id = movement["lot_id"]
        delta = movement["quantity_delta_units"]
        balances[lot_id] += delta
        used_ml += delta * lot_volume[lot_id]
        if used_ml > capacity:
            capacity_failures.append({"movement_id": movement["movement_id"], "used_ml": used_ml, "capacity_ml": capacity})
    checks.append(_check("warehouse_capacity_respected", capacity_failures))

    type_failures = []
    integer_columns = {
        "products": ("case_size_units", "storage_ml_per_unit", "normal_shelf_life_days"),
        "supplier_product_terms": ("purchase_cost_cents", "minimum_order_units"),
        "customer_order_lines": ("requested_units",),
        "supplier_order_lines": ("ordered_units", "unit_cost_cents"),
        "stock_movements": ("quantity_delta_units",),
    }
    for table, columns in integer_columns.items():
        for column in columns:
            count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE typeof({column}) != 'integer'").fetchone()[0]
            if count:
                type_failures.append({"table": table, "column": column, "invalid_rows": count})
    unit_failures = [dict(row) for row in db.execute("SELECT product_id, base_unit FROM products WHERE base_unit != 'each'")]
    checks.append(_check("quantities_money_and_units_are_declared", type_failures + unit_failures))

    known_failures = []
    for table in _known_tables(db):
        for row in db.execute(f"SELECT rowid, event_date, known_at FROM {table} WHERE known_at > event_date"):
            known_failures.append({"table": table, **dict(row)})
    checks.append(_check("knowledge_dates_do_not_follow_events", known_failures))

    manifest = dict(db.execute("SELECT key, value FROM dataset_manifest").fetchall())
    counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in _all_tables(db)}
    coverage = _coverage(db)
    if not foreign_keys:
        checks.extend(detailed_checks(db))
    if evaluator_path:
        evaluator = connect(evaluator_path, readonly=True)
        evaluator_fk = [dict(row) for row in evaluator.execute("PRAGMA foreign_key_check")]
        checks.append(_check("evaluator_foreign_keys_resolve", evaluator_fk))
        checks.append(continuation_check(db, evaluator))
        coverage["future_customer_orders"] = evaluator.execute("SELECT COUNT(*) FROM future_customer_orders").fetchone()[0]
        coverage["future_customer_order_units"] = evaluator.execute("SELECT COALESCE(SUM(requested_units),0) FROM future_customer_order_lines").fetchone()[0]
        evaluator.close()
    db.close()
    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "table_counts": counts, "coverage": coverage, "manifest": manifest}


def _known_tables(db) -> list[str]:
    tables = []
    for table in _all_tables(db):
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        if {"known_at", "event_date"} <= columns:
            tables.append(table)
    return tables


def _all_tables(db) -> list[str]:
    return [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def _coverage(db) -> dict:
    requested = db.execute("SELECT COALESCE(SUM(requested_units),0) FROM customer_order_lines").fetchone()[0]
    shipped = db.execute("SELECT COALESCE(SUM(shipped_units),0) FROM shipments").fetchone()[0]
    cancelled = db.execute("SELECT COALESCE(SUM(cancelled_units),0) FROM cancellations").fetchone()[0]
    expired = -db.execute("SELECT COALESCE(SUM(quantity_delta_units),0) FROM stock_movements WHERE movement_type='expiry'").fetchone()[0]
    closing_units = db.execute("SELECT COALESCE(SUM(closing_units),0) FROM closing_stock").fetchone()[0]
    outstanding_customer = requested - shipped - cancelled
    ordered = db.execute("SELECT COALESCE(SUM(ordered_units),0) FROM supplier_order_lines").fetchone()[0]
    received = db.execute("SELECT COALESCE(SUM(received_units),0) FROM receipts").fetchone()[0]
    result = {
        "historical_requested_units": requested,
        "historical_shipped_units": shipped,
        "historical_cancelled_units": cancelled,
        "historical_open_customer_units": outstanding_customer,
        "historical_fulfilment_percent": round(100 * shipped / requested, 2) if requested else None,
        "expiry_writeoff_units": expired,
        "closing_stock_units": closing_units,
        "supplier_ordered_units": ordered,
        "supplier_received_units": received,
        "supplier_outstanding_units": ordered - received,
    }
    result["on_time_shipped_units"] = db.execute("""SELECT COALESCE(SUM(s.shipped_units),0)
        FROM shipments s JOIN customer_order_lines l USING(customer_order_line_id)
        JOIN customer_orders o USING(customer_order_id) WHERE s.dispatch_date<=o.due_date""").fetchone()[0]
    result["closing_stock_value_cents"] = db.execute("""SELECT COALESCE(SUM(c.closing_units*l.acquisition_cost_cents),0)
        FROM closing_stock c JOIN stock_lots l USING(lot_id)""").fetchone()[0]
    result["expiry_writeoff_cents"] = db.execute("""SELECT COALESCE(SUM(-m.quantity_delta_units*l.acquisition_cost_cents),0)
        FROM stock_movements m JOIN stock_lots l USING(lot_id) WHERE m.movement_type='expiry'""").fetchone()[0]
    result["near_expiry_closing_units_30_days"] = db.execute("""SELECT COALESCE(SUM(c.closing_units),0)
        FROM closing_stock c JOIN stock_lots l USING(lot_id)
        WHERE julianday(l.expiry_date)-julianday(c.as_of_date) BETWEEN 1 AND 30""").fetchone()[0]
    result["supplier_outstanding_value_cents"] = db.execute("""SELECT COALESCE(SUM(
        (l.ordered_units-COALESCE((SELECT SUM(r.received_units) FROM receipts r
         WHERE r.supplier_order_line_id=l.supplier_order_line_id),0))*l.unit_cost_cents),0)
        FROM supplier_order_lines l""").fetchone()[0]
    return result


def write_audit(report: dict, path: Path) -> None:
    """Write the compact accepted audit report."""
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
