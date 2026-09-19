"""Deterministic raw-export to operational-ledger reconciliation."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
import json
from typing import Any

from .config import PHASE1_DIR
from .contracts import ImportedCase, ImportContractError, ReconciliationBlocked


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    """Load the frozen Phase 1 facts as configuration, never as output."""
    return json.loads((PHASE1_DIR / "contract.json").read_text(encoding="utf-8"))


def _words(value: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in value)
    return {word for word in cleaned.split() if not word.isdigit()}


def _validate_information_boundary(imported: ImportedCase, contract: dict[str, Any]) -> None:
    """Reject dated facts that were not effective or known at decision time."""
    decision_at = datetime.fromisoformat(contract["decision_timestamp"])
    decision_day = decision_at.date()
    for row in imported.rows["products.csv"]:
        if not (date.fromisoformat(row["cost_effective_from"]) <= decision_day <= date.fromisoformat(row["cost_effective_to"])):
            raise ImportContractError(f"Product cost is not effective at decision time: {row['source_row_id']}")
    for row in imported.rows["supplier_terms.csv"]:
        if row["minimum_merchandise_eur"] and not (
            date.fromisoformat(row["effective_from"]) <= decision_day <= date.fromisoformat(row["effective_to"])
        ):
            raise ImportContractError(f"Supplier term is not effective at decision time: {row['source_row_id']}")
    dated_fields = {
        "stock_snapshot.csv": "snapshot_at",
        "customer_orders.csv": "booked_at",
        "purchase_orders.csv": "ordered_at",
        "receipts.csv": "received_at",
    }
    for filename, field in dated_fields.items():
        for row in imported.rows[filename]:
            if datetime.fromisoformat(row[field]) > decision_at:
                raise ImportContractError(f"Future-known record cannot enter the decision: {row['source_row_id']}")


def _product_map(imported: ImportedCase, contract: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for row in imported.rows["products.csv"]:
        matches = [
            product
            for product in contract["products"]
            if int(row["case_size"]) == product["case_size"]
            and row["base_uom"] == product["base_uom"]
            and Decimal(row["unit_cost_eur"]) == Decimal(product["unit_cost_eur"])
            and _words(product["name"]) <= _words(row["description"])
        ]
        if len(matches) != 1:
            raise ImportContractError(f"Product master row is not uniquely identifiable: {row['source_row_id']}")
        output[row["product_ref"]] = matches[0]["product_id"]
    for row in imported.rows["resolutions.csv"]:
        if row["resolution_type"] == "automatic_alias_mapping":
            affected = next(issue for issue in imported.issues if issue.issue_id == row["issue_id"])
            for source_id in affected.affected_rows:
                for file_rows in imported.rows.values():
                    matched = next((item for item in file_rows if item.get("source_row_id") == source_id), None)
                    if matched and matched.get("product_ref"):
                        output[matched["product_ref"]] = row["chosen_value"]
    return output


def _supplier_map(imported: ImportedCase, contract: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for row in imported.rows["supplier_terms.csv"]:
        if not row["minimum_merchandise_eur"]:
            continue
        matches = [
            supplier
            for supplier in contract["suppliers"]
            if int(row["lead_time_workdays"]) == supplier["lead_time_workdays"]
            and Decimal(row["minimum_merchandise_eur"]) == Decimal(supplier["minimum_merchandise_eur"])
            and Decimal(row["delivery_charge_eur"]) == Decimal(supplier["delivery_charge_eur"])
        ]
        if len(matches) != 1:
            raise ImportContractError(f"Supplier term is not uniquely identifiable: {row['source_row_id']}")
        output[row["supplier_ref"]] = matches[0]["supplier_id"]
    return output


def _opening_stock(imported: ImportedCase, product_map: dict[str, str]) -> list[dict[str, Any]]:
    output = []
    for row in imported.rows["stock_snapshot.csv"]:
        sources = [row["source_row_id"]]
        linked_receipts = [
            receipt
            for receipt in imported.rows["receipts.csv"]
            if receipt["lot_ref"] == row["lot_ref"] and receipt["product_ref"] == row["product_ref"]
        ]
        sources.extend(receipt["source_row_id"] for receipt in linked_receipts)
        output.append({
            "product_id": product_map[row["product_ref"]],
            "lot_id": row["lot_ref"],
            "quantity_units": int(row["quantity"]),
            "expiry_date": row["expiry_date"],
            "source_row_ids": sources,
        })
    return sorted(output, key=lambda value: (value["product_id"], value["lot_id"]))


def _bookings(imported: ImportedCase, product_map: dict[str, str]) -> list[dict[str, Any]]:
    by_line: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in imported.rows["customer_orders.csv"]:
        by_line[row["line_ref"]].append(row)
    output = []
    for line_id, versions in sorted(by_line.items()):
        active = [row for row in versions if row["status"] != "superseded"]
        if len(active) != 1:
            raise ImportContractError(f"Expected exactly one active customer line: {line_id}")
        row = active[0]
        output.append({
            "line_id": line_id,
            "customer_id": row["customer_ref"],
            "product_id": product_map[row["product_ref"]],
            "quantity_units": int(row["quantity"]),
            "due_date": row["due_date"],
            "source_row_ids": [version["source_row_id"] for version in sorted(versions, key=lambda value: int(value["amendment_sequence"]))],
        })
    return output


def _buyer_basket(
    imported: ImportedCase,
    product_map: dict[str, str],
    contract_products: dict[str, dict[str, Any]],
    supplier: dict[str, Any],
) -> dict[str, Any]:
    resolutions = {row["issue_id"]: row for row in imported.rows["resolutions.csv"]}
    lines = []
    arrivals = set()
    for row in imported.rows["purchase_orders.csv"]:
        if row["status"] != "draft":
            continue
        product_id = product_map[row["product_ref"]]
        product = contract_products[product_id]
        uom = row["uom"]
        sources = [row["source_row_id"]]
        if not uom:
            if "ISS-002" not in imported.approved_issue_ids or "ISS-002" not in resolutions:
                raise ReconciliationBlocked("ISS-002 must be confirmed before quantity conversion")
            uom = resolutions["ISS-002"]["chosen_value"]
            sources.append(resolutions["ISS-002"]["resolution_id"])
        if uom != "case":
            raise ImportContractError(f"Draft order UOM must be case: {row['source_row_id']}")
        cases = int(row["quantity"])
        units = cases * product["case_size"]
        line_value = Decimal(product["unit_cost_eur"]) * units
        arrivals.add(row["expected_date"])
        lines.append({
            "product_id": product_id,
            "cases": cases,
            "quantity_units": units,
            "line_value_eur": f"{line_value:.2f}",
            "source_row_ids": sources,
        })
    if len(arrivals) != 1:
        raise ImportContractError("Buyer basket must have one expected arrival date")
    lines.sort(key=lambda value: value["product_id"])
    merchandise = sum(Decimal(row["line_value_eur"]) for row in lines)
    delivery = Decimal(supplier["delivery_charge_eur"])
    return {
        "arrival_date": arrivals.pop(),
        "lines": lines,
        "merchandise_eur": f"{merchandise:.2f}",
        "delivery_charge_eur": f"{delivery:.2f}",
        "immediate_cash_eur": f"{merchandise + delivery:.2f}",
    }


def _known_incoming(
    imported: ImportedCase,
    product_map: dict[str, str],
    contract_products: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for original in (row for row in imported.rows["purchase_orders.csv"] if row["status"] == "partially_received"):
        product_id = product_map[original["product_ref"]]
        product = contract_products[product_id]
        ordered = int(original["quantity"]) * product["case_size"]
        receipts = [
            row for row in imported.rows["receipts.csv"]
            if row["purchase_order_ref"] == original["purchase_order_ref"] and row["line_ref"] == original["line_ref"]
        ]
        received = sum(int(row["quantity"]) * product["case_size"] if row["uom"] == "case" else int(row["quantity"]) for row in receipts)
        updates = [
            row for row in imported.rows["purchase_orders.csv"]
            if row["status"] == "outstanding_eta_update"
            and row["purchase_order_ref"] == original["purchase_order_ref"]
            and row["line_ref"] == original["line_ref"]
        ]
        if len(updates) != 1:
            raise ImportContractError("Partial purchase requires one revised ETA row")
        remaining = ordered - received
        update = updates[0]
        if remaining != int(update["quantity"]) * product["case_size"]:
            raise ImportContractError("Outstanding ETA quantity does not reconcile")
        expiry = receipts[0]["expiry_date"] if receipts else product["incoming_expiry_date"]
        output.append({
            "product_id": product_id,
            "quantity_units": remaining,
            "arrival_date": update["expected_date"],
            "expiry_date": expiry,
            "source_row_ids": [original["source_row_id"], update["source_row_id"], *[row["source_row_id"] for row in receipts]],
        })
    return sorted(output, key=lambda value: (value["arrival_date"], value["product_id"]))


def reconcile(imported: ImportedCase) -> dict[str, Any]:
    """Produce the canonical ledger or stop on unresolved critical ambiguity."""
    if imported.blocked:
        blockers = ", ".join(issue.issue_id for issue in imported.issues if issue.blocks_planning)
        raise ReconciliationBlocked(f"Planning blocked by unresolved issues: {blockers}")
    contract = load_contract()
    _validate_information_boundary(imported, contract)
    contract_cases = {row["case_id"]: row for row in contract["cases"]}
    contract_products = {row["product_id"]: row for row in contract["products"]}
    contract_suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    case_contract = contract_cases[imported.case_id]
    product_map = _product_map(imported, contract)
    supplier_map = _supplier_map(imported, contract)
    primary_supplier = contract_suppliers[case_contract["supplier_id"]]
    draft_supplier_refs = {row["supplier_ref"] for row in imported.rows["purchase_orders.csv"] if row["status"] == "draft"}
    if not draft_supplier_refs or {supplier_map.get(value) for value in draft_supplier_refs} != {case_contract["supplier_id"]}:
        raise ImportContractError("Draft basket supplier does not reconcile to the case contract")
    case = {
        "case_id": imported.case_id,
        "supplier_id": case_contract["supplier_id"],
        "opening_stock": _opening_stock(imported, product_map),
        "known_incoming": _known_incoming(imported, product_map, contract_products),
        "booked_lines": _bookings(imported, product_map),
        "buyer_basket": _buyer_basket(imported, product_map, contract_products, primary_supplier),
        "unresolved_blockers": [],
    }
    if imported.case_id == "no_change_control":
        if "ISS-005" not in imported.approved_issue_ids:
            raise ReconciliationBlocked("ISS-005 must be resolved with an authoritative supplier term")
        case["initial_blocker"] = "ISS-005"
    canonical = json.dumps(case, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "schema_version": "1.0",
        "contract_version": contract["contract_version"],
        "case_id": imported.case_id,
        "input_hash": imported.input_hash,
        "output_hash": sha256(canonical.encode("utf-8")).hexdigest(),
        "source_row_count": sum(len(rows) for rows in imported.rows.values()),
        "issues": [
            {
                "issue_id": issue.issue_id,
                "classification": issue.classification,
                "status": issue.status,
                "affected_rows": list(issue.affected_rows),
                "resolution_id": issue.resolution_id,
            }
            for issue in imported.issues
        ],
        "case": case,
    }


def stable_reconcile(imported: ImportedCase) -> dict[str, Any]:
    """Reconcile twice and prove deterministic, idempotent output."""
    first = reconcile(imported)
    second = reconcile(deepcopy(imported))
    if first != second:
        raise AssertionError("Reconciliation is not deterministic")
    return first
