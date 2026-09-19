"""Strict import and traceable reconciliation for frozen example exports."""

from __future__ import annotations

import csv
from datetime import datetime
import hashlib
from io import StringIO
from pathlib import Path
from typing import Any

from .config import CASE_LABELS, EXPECTED_FILES, MAX_FILE_BYTES, RAW_DIR, REQUIRED_VIEWS
from .contracts import DataIssue, ImportedCase, ImportContractError, ReconciliationBlocked


SCHEMAS = {
    "products.csv": ("row_id", "product_id", "product_name", "supplier_id", "case_size", "unit_cost_eur", "date_type", "new_receipt_expiry_date", "max_new_cases"),
    "product_aliases.csv": ("row_id", "product_ref", "product_id"),
    "stock_lots.csv": ("row_id", "case_id", "product_ref", "lot_id", "quantity", "uom", "expiry_date", "stock_status"),
    "customer_orders.csv": ("row_id", "case_id", "line_id", "customer_id", "product_ref", "quantity_units", "due_date", "min_shelf_life_days", "status", "known_at"),
    "purchases.csv": ("row_id", "case_id", "line_id", "product_ref", "cases", "status", "expected_arrival", "expiry_date", "change_cutoff", "amends_row_id"),
    "supplier_terms.csv": ("row_id", "case_id", "supplier_id", "review_date", "order_weekday", "lead_days", "delivery_charge_eur", "budget_eur", "receipt_capacity_units", "effective_from", "effective_to"),
    "demand_views.csv": ("row_id", "case_id", "view_id", "event_id", "product_ref", "quantity_units", "due_date", "min_shelf_life_days", "known_at"),
}


def _parse(name: str, text: str) -> list[dict[str, str]]:
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise ImportContractError(f"{name} exceeds the example file limit")
    reader = csv.DictReader(StringIO(text))
    if tuple(reader.fieldnames or ()) != SCHEMAS[name]:
        raise ImportContractError(f"{name} does not match the frozen schema")
    return list(reader)


def import_files(files: dict[str, str], approved_issue_ids: set[str] | None = None) -> ImportedCase:
    """Validate seven named CSVs and expose decision-critical ambiguities."""
    if set(files) != set(EXPECTED_FILES):
        raise ImportContractError("Expected seven named CSVs")
    rows = {name: _parse(name, files[name]) for name in EXPECTED_FILES}
    all_ids = [row["row_id"] for values in rows.values() for row in values]
    if len(all_ids) != len(set(all_ids)):
        raise ImportContractError("row_id values must be globally unique")
    case_ids = {row["case_id"] for name, values in rows.items() if "case_id" in SCHEMAS[name] for row in values}
    if len(case_ids) != 1 or next(iter(case_ids)) not in CASE_LABELS:
        raise ImportContractError("Files must contain one known example case")
    case_id = next(iter(case_ids))
    approved = set(approved_issue_ids or ())
    issues: list[DataIssue] = []
    blank_uom = [row for row in rows["stock_lots.csv"] if not row["uom"]]
    if blank_uom:
        issues.append(DataIssue(
            issue_id="SW-ISS-001",
            classification="buyer_confirmation_required",
            title="Confirm five cases of Oat Crackers",
            detail="The warehouse export says 5 but omits the unit. The signed count sheet records five 12-unit cases.",
            status="resolved" if "SW-ISS-001" in approved else "pending",
            affected_rows=tuple(row["row_id"] for row in blank_uom),
            action_label="Confirm 60 units",
        ))
    aliases = {row["product_ref"]: row["product_id"] for row in rows["product_aliases.csv"]}
    products = {row["product_id"] for row in rows["products.csv"]}
    for name in ("stock_lots.csv", "customer_orders.csv", "purchases.csv", "demand_views.csv"):
        for row in rows[name]:
            ref = row["product_ref"]
            if ref not in products and ref not in aliases:
                raise ImportContractError(f"Unknown product reference {ref} in {row['row_id']}")
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(files[name].encode())
    return ImportedCase(case_id, digest.hexdigest(), dict(files), rows, issues, approved)


def approve_issue(imported: ImportedCase, issue_id: str) -> ImportedCase:
    """Return a fresh import with one supported buyer confirmation applied."""
    if issue_id not in {issue.issue_id for issue in imported.issues}:
        raise ImportContractError(f"Unknown issue {issue_id}")
    return import_files(imported.files, imported.approved_issue_ids | {issue_id})


def load_example(case_id: str) -> ImportedCase:
    """Load one frozen example package from disk."""
    if case_id not in CASE_LABELS:
        raise ImportContractError(f"Unknown example {case_id}")
    folder = RAW_DIR / case_id
    return import_files({name: (folder / name).read_text(encoding="utf-8") for name in EXPECTED_FILES})


def _integer(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ImportContractError(f"{label} must be a whole number") from exc
    if parsed < 0:
        raise ImportContractError(f"{label} cannot be negative")
    return parsed


def reconcile(imported: ImportedCase) -> dict[str, Any]:
    """Create the exact lot, commitment, purchase and demand position."""
    if imported.blocked:
        raise ReconciliationBlocked("Resolve the buyer confirmation before calculating the plan")
    rows = imported.rows
    aliases = {row["product_ref"]: row["product_id"] for row in rows["product_aliases.csv"]}
    canonical = lambda ref: aliases.get(ref, ref)
    products = {}
    for row in rows["products.csv"]:
        products[row["product_id"]] = {
            "product_id": row["product_id"], "product_name": row["product_name"], "supplier_id": row["supplier_id"],
            "case_size": _integer(row["case_size"], "case_size"), "unit_cost_eur": row["unit_cost_eur"],
            "date_type": row["date_type"], "new_receipt_expiry_date": row["new_receipt_expiry_date"],
            "max_new_cases": _integer(row["max_new_cases"], "max_new_cases"), "source_row_ids": [row["row_id"]],
        }
    term = rows["supplier_terms.csv"][0]
    review_date = term["review_date"]
    for name in ("customer_orders.csv", "demand_views.csv"):
        for row in rows[name]:
            if row["known_at"][:10] > review_date:
                raise ImportContractError(f"Future-known record {row['row_id']}")
    lots = []
    for row in rows["stock_lots.csv"]:
        product = products[canonical(row["product_ref"])]
        quantity = _integer(row["quantity"], "stock quantity")
        if row["uom"] == "CASE" or not row["uom"]:
            quantity *= product["case_size"]
        elif row["uom"] != "EA":
            raise ImportContractError(f"Unsupported UOM in {row['row_id']}")
        lots.append({
            "lot_id": row["lot_id"], "product_id": product["product_id"], "quantity_units": quantity,
            "expiry_date": row["expiry_date"], "stock_status": row["stock_status"], "source_row_ids": [row["row_id"]],
        })
    orders = [{
        "line_id": row["line_id"], "customer_id": row["customer_id"], "product_id": canonical(row["product_ref"]),
        "quantity_units": _integer(row["quantity_units"], "order quantity"), "due_date": row["due_date"],
        "min_shelf_life_days": _integer(row["min_shelf_life_days"], "minimum shelf life"), "source_row_ids": [row["row_id"]],
    } for row in rows["customer_orders.csv"] if row["status"] == "booked"]
    purchase_rows = rows["purchases.csv"]
    superseded = {row["amends_row_id"] for row in purchase_rows if row["amends_row_id"]}
    purchases = []
    for row in purchase_rows:
        if row["row_id"] in superseded or row["status"] != "open":
            continue
        source_ids = [row["row_id"]]
        if row["amends_row_id"]:
            source_ids.insert(0, row["amends_row_id"])
        purchases.append({
            "line_id": row["line_id"], "product_id": canonical(row["product_ref"]), "cases": _integer(row["cases"], "purchase cases"),
            "expected_arrival": row["expected_arrival"], "expiry_date": row["expiry_date"], "change_cutoff": row["change_cutoff"],
            "source_row_ids": source_ids,
        })
    demand_views = {view: [] for view in REQUIRED_VIEWS}
    for row in rows["demand_views.csv"]:
        if row["view_id"] not in demand_views:
            raise ImportContractError(f"Unknown demand view {row['view_id']}")
        demand_views[row["view_id"]].append({
            "event_id": row["event_id"], "product_id": canonical(row["product_ref"]),
            "quantity_units": _integer(row["quantity_units"], "demand quantity"), "due_date": row["due_date"],
            "min_shelf_life_days": _integer(row["min_shelf_life_days"], "minimum shelf life"), "source_row_ids": [row["row_id"]],
        })
    supplier = {
        "supplier_id": term["supplier_id"], "review_date": review_date, "order_weekday": term["order_weekday"],
        "lead_days": _integer(term["lead_days"], "lead days"), "delivery_charge_eur": term["delivery_charge_eur"],
        "budget_eur": term["budget_eur"], "receipt_capacity_units": _integer(term["receipt_capacity_units"], "receipt capacity"),
        "effective_from": term["effective_from"], "effective_to": term["effective_to"], "source_row_ids": [term["row_id"]],
    }
    return {
        "case_id": imported.case_id, "input_hash": imported.input_hash, "products": products, "lots": lots,
        "booked_orders": orders, "purchases": purchases, "supplier": supplier, "demand_views": demand_views,
        "source_row_count": sum(len(value) for value in rows.values()),
    }
