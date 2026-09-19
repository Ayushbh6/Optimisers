"""Strict, provenance-preserving import for the showcase CSV bundle."""

from __future__ import annotations

import csv
from dataclasses import replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

from .config import CASE_PREFIXES, EXPECTED_FILES, ISSUE_REGISTER_PATH, MAX_FILE_BYTES, MAX_UPLOAD_BYTES, RAW_DIR
from .contracts import ImportContractError, ImportedCase, ImportIssue


SCHEMAS = {
    "products.csv": ("source_row_id", "source_system", "product_ref", "description", "supplier_ref", "base_uom", "case_size", "product_min_cases", "unit_cost_eur", "cost_effective_from", "cost_effective_to"),
    "supplier_terms.csv": ("source_row_id", "source_system", "supplier_ref", "supplier_name", "order_weekday", "lead_time_workdays", "minimum_merchandise_eur", "delivery_charge_eur", "effective_from", "effective_to"),
    "stock_snapshot.csv": ("source_row_id", "source_system", "snapshot_at", "product_ref", "lot_ref", "quantity", "uom", "expiry_date"),
    "customer_orders.csv": ("source_row_id", "source_system", "order_ref", "line_ref", "amendment_sequence", "status", "customer_ref", "product_ref", "quantity", "uom", "booked_at", "due_date"),
    "purchase_orders.csv": ("source_row_id", "source_system", "purchase_order_ref", "line_ref", "supplier_ref", "product_ref", "quantity", "uom", "ordered_at", "expected_date", "status"),
    "receipts.csv": ("source_row_id", "source_system", "receipt_ref", "purchase_order_ref", "line_ref", "product_ref", "quantity", "uom", "received_at", "lot_ref", "expiry_date"),
    "resolutions.csv": ("resolution_id", "issue_id", "resolution_type", "chosen_value", "evidence_ref", "resolved_by", "resolved_at"),
}


def _parse_file(name: str, content: str) -> list[dict[str, str]]:
    try:
        reader = csv.DictReader(StringIO(content, newline=""))
        if tuple(reader.fieldnames or ()) != SCHEMAS[name]:
            raise ImportContractError(f"{name}: columns do not match the frozen schema")
        rows = list(reader)
    except csv.Error as exc:
        raise ImportContractError(f"{name}: invalid CSV: {exc}") from exc
    id_field = "resolution_id" if name == "resolutions.csv" else "source_row_id"
    for index, row in enumerate(rows, start=2):
        if not row[id_field] or not row.get("source_system", "resolution_record"):
            raise ImportContractError(f"{name}:{index}: source identity is required")
    return rows


def _identify_case(rows: dict[str, list[dict[str, str]]]) -> str:
    ids = []
    for name, file_rows in rows.items():
        id_field = "resolution_id" if name == "resolutions.csv" else "source_row_id"
        ids.extend(row[id_field] for row in file_rows)
    prefixes = {value.split("-", 1)[0] for value in ids}
    if len(prefixes) != 1 or next(iter(prefixes)) not in CASE_PREFIXES:
        raise ImportContractError("All uploaded rows must belong to one declared showcase case")
    return CASE_PREFIXES[next(iter(prefixes))]


def _issues(case_id: str, rows: dict[str, list[dict[str, str]]], approved: set[str]) -> list[ImportIssue]:
    """Materialise the frozen, independently reviewed issue contract for one upload.

    The register defines what each defect means; the importer verifies that its
    cited source and resolution rows are actually present in the uploaded bytes.
    """
    register = json.loads(ISSUE_REGISTER_PATH.read_text(encoding="utf-8"))["issues"]
    relevant = [item for item in register if item["case_id"] in {case_id, "all"}]
    source_ids = {
        row["source_row_id"]
        for name, file_rows in rows.items()
        if name != "resolutions.csv"
        for row in file_rows
    }
    resolutions = {row["issue_id"]: row for row in rows["resolutions.csv"]}
    actions = {
        "buyer_confirmation_required": "Confirm recorded UOM",
        "hard_blocker": "Use authoritative term",
    }
    titles = {
        "automatic_alias_mapping": "Product alias matched",
        "buyer_confirmation": "Confirm draft-order UOM",
        "linked_partial_receipt": "Partial receipt reconciled",
        "automatic_supplier_mapping": "Supplier alias matched",
        "linked_po_receipt_reconciliation": "Receipt counted once",
        "latest_numbered_amendment": "Customer amendment applied",
        "authoritative_replacement": "Supplier minimum restored",
    }
    output: list[ImportIssue] = []
    for item in relevant:
        resolution = resolutions.get(item["issue_id"])
        if resolution is None:
            raise ImportContractError(f"Missing contracted resolution evidence: {item['issue_id']}")
        expected_rows = tuple(
            source_id
            for source_id in item["affected_source_row_ids"]
            if source_id.split("-", 1)[0] == next(iter(source_ids)).split("-", 1)[0]
        )
        missing = sorted(set(expected_rows) - source_ids)
        if missing:
            raise ImportContractError(f"Issue {item['issue_id']} cites missing source rows: {missing}")
        requires_action = item["classification"] in actions
        status = "resolved" if not requires_action or item["issue_id"] in approved else "pending"
        output.append(ImportIssue(
            item["issue_id"],
            item["classification"],
            titles[resolution["resolution_type"]],
            item["business_cause"],
            status,
            expected_rows,
            resolution["resolution_id"],
            actions.get(item["classification"]),
        ))
    return output


def import_files(files: dict[str, str], *, approved_issue_ids: set[str] | None = None) -> ImportedCase:
    """Validate and preserve one complete seven-file upload."""
    if set(files) != set(EXPECTED_FILES):
        missing = sorted(set(EXPECTED_FILES) - set(files))
        extra = sorted(set(files) - set(EXPECTED_FILES))
        raise ImportContractError(f"Expected seven named CSVs; missing={missing}, extra={extra}")
    total = sum(len(content.encode("utf-8")) for content in files.values())
    if total > MAX_UPLOAD_BYTES:
        raise ImportContractError("Upload exceeds the 5 MB session limit")
    if any(len(content.encode("utf-8")) > MAX_FILE_BYTES for content in files.values()):
        raise ImportContractError("One CSV exceeds the 1 MB file limit")
    rows = {name: _parse_file(name, files[name]) for name in EXPECTED_FILES}
    identifiers: list[str] = []
    for name, file_rows in rows.items():
        id_field = "resolution_id" if name == "resolutions.csv" else "source_row_id"
        identifiers.extend(row[id_field] for row in file_rows)
    if len(identifiers) != len(set(identifiers)):
        raise ImportContractError("Source row identifiers must be globally unique within the session")
    case_id = _identify_case(rows)
    canonical = json.dumps({name: files[name] for name in sorted(files)}, ensure_ascii=False, separators=(",", ":"))
    input_hash = sha256(canonical.encode("utf-8")).hexdigest()
    approved = set(approved_issue_ids or ())
    return ImportedCase(case_id, input_hash, dict(files), rows, _issues(case_id, rows, approved), approved)


def approve_issue(imported: ImportedCase, issue_id: str) -> ImportedCase:
    """Apply one recorded explicit confirmation and recompute issue state."""
    issue = next((row for row in imported.issues if row.issue_id == issue_id), None)
    if issue is None or issue.classification not in {"buyer_confirmation_required", "hard_blocker"}:
        raise ImportContractError("Issue is not an explicit buyer action")
    resolution_ids = {row["issue_id"] for row in imported.rows["resolutions.csv"]}
    if issue_id not in resolution_ids:
        raise ImportContractError("No evidence-backed resolution exists for this issue")
    approved = set(imported.approved_issue_ids) | {issue_id}
    return replace(imported, issues=_issues(imported.case_id, imported.rows, approved), approved_issue_ids=approved)


def load_example(case_id: str, *, approved_issue_ids: set[str] | None = None) -> ImportedCase:
    """Load one frozen example through the same bytes accepted by uploads."""
    case_dir = RAW_DIR / case_id
    if not case_dir.is_dir():
        raise ImportContractError(f"Unknown example: {case_id}")
    files = {name: (case_dir / name).read_text(encoding="utf-8") for name in EXPECTED_FILES}
    return import_files(files, approved_issue_ids=approved_issue_ids)
