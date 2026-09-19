"""Independent Phase 2 fixture audit.

This is not application import code. It reads the raw showcase exports through
the Python standard library, reconstructs their operational meaning, and checks
that meaning against the separately frozen Phase 1 contract and golden ledger.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


PHASE2 = Path(__file__).resolve().parent
ROOT = PHASE2.parents[2]
RAW = PHASE2 / "raw"
GOLDEN = PHASE2 / "golden" / "normalized-ledger.json"
ISSUES = PHASE2 / "issue-register.json"
ACCOUNTING = PHASE2 / "row-accounting.csv"
MANIFEST = PHASE2 / "manifest.json"
PHASE1_CONTRACT = ROOT / "artifacts" / "supplier-basket-showcase" / "phase-1" / "contract.json"
PHASE1_EXPECTED = ROOT / "artifacts" / "supplier-basket-showcase" / "phase-1" / "expected-results.json"

SCHEMAS = {
    "products.csv": ["source_row_id", "source_system", "product_ref", "description", "supplier_ref", "base_uom", "case_size", "product_min_cases", "unit_cost_eur", "cost_effective_from", "cost_effective_to"],
    "supplier_terms.csv": ["source_row_id", "source_system", "supplier_ref", "supplier_name", "order_weekday", "lead_time_workdays", "minimum_merchandise_eur", "delivery_charge_eur", "effective_from", "effective_to"],
    "stock_snapshot.csv": ["source_row_id", "source_system", "snapshot_at", "product_ref", "lot_ref", "quantity", "uom", "expiry_date"],
    "customer_orders.csv": ["source_row_id", "source_system", "order_ref", "line_ref", "amendment_sequence", "status", "customer_ref", "product_ref", "quantity", "uom", "booked_at", "due_date"],
    "purchase_orders.csv": ["source_row_id", "source_system", "purchase_order_ref", "line_ref", "supplier_ref", "product_ref", "quantity", "uom", "ordered_at", "expected_date", "status"],
    "receipts.csv": ["source_row_id", "source_system", "receipt_ref", "purchase_order_ref", "line_ref", "product_ref", "quantity", "uom", "received_at", "lot_ref", "expiry_date"],
    "resolutions.csv": ["resolution_id", "issue_id", "resolution_type", "chosen_value", "evidence_ref", "resolved_by", "resolved_at"],
}

ALLOWED_ACCOUNTING_STATES = {
    "accepted_as_supplied",
    "accepted_after_safe_normalization",
    "superseded_by_amendment",
    "accepted_after_buyer_confirmation",
    "accepted_after_authoritative_replacement",
    "blocked_unresolved",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == SCHEMAS[path.name], f"schema mismatch: {path}"
        return list(reader)


def normal_words(value: str) -> set[str]:
    return {word for word in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split() if not word.isdigit()}


@dataclass(frozen=True)
class AuditResult:
    raw_files: int
    source_rows: int
    accounted_rows: int
    issues: int
    cases: int
    booked_units: int
    buyer_cash_eur: Decimal


def audit() -> AuditResult:
    contract = load_json(PHASE1_CONTRACT)
    expected = load_json(PHASE1_EXPECTED)
    golden = load_json(GOLDEN)
    issue_register = load_json(ISSUES)
    contract_products = {row["product_id"]: row for row in contract["products"]}
    contract_suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    contract_cases = {row["case_id"]: row for row in contract["cases"]}
    expected_cases = {row["case_id"]: row for row in expected["cases"]}
    golden_cases = {row["case_id"]: row for row in golden["cases"]}
    decision_at = datetime.fromisoformat(contract["decision_timestamp"])
    decision_date = decision_at.date()

    if MANIFEST.exists():
        manifest = load_json(MANIFEST)
        for relative_path, expected_hash in manifest["file_hashes_sha256"].items():
            assert sha256(ROOT / relative_path) == expected_hash, f"hash mismatch: {relative_path}"
        assert sha256(PHASE1_CONTRACT) == manifest["phase_1_sources_sha256"][str(PHASE1_CONTRACT.relative_to(ROOT))]
        assert sha256(PHASE1_EXPECTED) == manifest["phase_1_sources_sha256"][str(PHASE1_EXPECTED.relative_to(ROOT))]

    raw: dict[str, dict[str, list[dict[str, str]]]] = {}
    raw_ids: set[tuple[str, str, str]] = set()
    id_index: dict[str, tuple[str, str, dict[str, str]]] = {}
    file_count = 0
    for case_dir in sorted(path for path in RAW.iterdir() if path.is_dir()):
        raw[case_dir.name] = {}
        assert set(path.name for path in case_dir.glob("*.csv")) == set(SCHEMAS)
        for path in sorted(case_dir.glob("*.csv")):
            rows = read_csv(path)
            raw[case_dir.name][path.name] = rows
            file_count += 1
            id_field = "resolution_id" if path.name == "resolutions.csv" else "source_row_id"
            for row in rows:
                row_id = row[id_field]
                key = (case_dir.name, path.name, row_id)
                assert key not in raw_ids and row_id not in id_index, f"duplicate source id: {row_id}"
                raw_ids.add(key)
                id_index[row_id] = (case_dir.name, path.name, row)

                if path.name == "customer_orders.csv":
                    assert datetime.fromisoformat(row["booked_at"]) < decision_at
                elif path.name == "purchase_orders.csv":
                    assert datetime.fromisoformat(row["ordered_at"]) < decision_at
                elif path.name == "receipts.csv":
                    assert datetime.fromisoformat(row["received_at"]) < decision_at
                elif path.name == "stock_snapshot.csv":
                    assert datetime.fromisoformat(row["snapshot_at"]) < decision_at
                elif path.name == "resolutions.csv":
                    assert datetime.fromisoformat(row["resolved_at"]) < decision_at
                elif path.name in {"products.csv", "supplier_terms.csv"}:
                    assert date.fromisoformat(row["cost_effective_from"] if path.name == "products.csv" else row["effective_from"]) <= decision_date
                    assert date.fromisoformat(row["cost_effective_to"] if path.name == "products.csv" else row["effective_to"]) >= decision_date

    with ACCOUNTING.open(newline="", encoding="utf-8") as handle:
        accounting_rows = list(csv.DictReader(handle))
    accounted = {(row["case_id"], row["file"], row["source_row_id"]) for row in accounting_rows}
    assert len(accounted) == len(accounting_rows), "duplicate row-accounting entry"
    assert accounted == raw_ids, "row accounting must cover every raw row exactly once"
    assert {row["state"] for row in accounting_rows} <= ALLOWED_ACCOUNTING_STATES
    assert all(row["state"] != "blocked_unresolved" for row in accounting_rows)

    issues = {row["issue_id"]: row for row in issue_register["issues"]}
    assert set(issues) == {f"ISS-{number:03d}" for number in range(1, 8)}
    resolution_ids = {row_id for row_id, (_, filename, _) in id_index.items() if filename == "resolutions.csv"}
    for issue in issues.values():
        assert issue["affected_source_row_ids"], issue["issue_id"]
        assert all(row_id in id_index for row_id in issue["affected_source_row_ids"])
        linked = issue.get("resolution_row_ids", [issue.get("resolution_row_id")])
        assert all(row_id in resolution_ids for row_id in linked if row_id)
        assert not issue["final_status"].endswith("unresolved")
    assert issues["ISS-002"]["initial_status"] == "blocked"
    assert issues["ISS-005"]["initial_status"] == "blocked"

    # Match raw product-master rows to frozen products using business attributes,
    # not source-row names or golden IDs.
    product_ref_to_id: dict[str, str] = {}
    for case_files in raw.values():
        for row in case_files["products.csv"]:
            matches = []
            row_words = normal_words(row["description"])
            for product_id, product in contract_products.items():
                if (
                    int(row["case_size"]) == product["case_size"]
                    and row["base_uom"] == product["base_uom"]
                    and Decimal(row["unit_cost_eur"]) == Decimal(product["unit_cost_eur"])
                    and normal_words(product["name"]) <= row_words
                ):
                    matches.append(product_id)
            assert len(matches) == 1, f"product master is not uniquely identifiable: {row}"
            product_ref_to_id[row["product_ref"]] = matches[0]

    positive_resolutions = {row["issue_id"]: row for row in raw["positive_moq_composition"]["resolutions.csv"]}
    product_ref_to_id["Tom Soup 12x400g"] = positive_resolutions["ISS-001"]["chosen_value"]

    # Complete current term rows identify supplier references independently by
    # lead time, minimum and charge. The incomplete control row is excluded.
    supplier_ref_to_id: dict[str, str] = {}
    for case_files in raw.values():
        for row in case_files["supplier_terms.csv"]:
            if not row["minimum_merchandise_eur"]:
                continue
            matches = [
                supplier_id
                for supplier_id, supplier in contract_suppliers.items()
                if int(row["lead_time_workdays"]) == supplier["lead_time_workdays"]
                and Decimal(row["minimum_merchandise_eur"]) == Decimal(supplier["minimum_merchandise_eur"])
                and Decimal(row["delivery_charge_eur"]) == Decimal(supplier["delivery_charge_eur"])
            ]
            assert len(matches) == 1
            supplier_ref_to_id[row["supplier_ref"]] = matches[0]

    booked_total = 0
    cash_total = Decimal("0")
    for case_id, phase1_case in contract_cases.items():
        files = raw[case_id]
        gold = golden_cases[case_id]

        # Opening stock.
        opening = sorted(
            (
                product_ref_to_id[row["product_ref"]],
                row["lot_ref"],
                int(row["quantity"]),
                row["expiry_date"],
            )
            for row in files["stock_snapshot.csv"]
        )
        gold_opening = sorted(
            (row["product_id"], row["lot_id"], row["quantity_units"], row["expiry_date"])
            for row in gold["opening_stock"]
        )
        contract_opening = sorted(
            (row["product_id"], row["lot_id"], row["quantity_units"], row["expiry_date"])
            for row in phase1_case["opening_lots"]
        )
        assert opening == gold_opening == contract_opening

        # Latest active customer-order amendment.
        by_line: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in files["customer_orders.csv"]:
            by_line[row["line_ref"]].append(row)
        bookings = []
        for line_id, versions in by_line.items():
            active = [row for row in versions if row["status"] != "superseded"]
            assert len(active) == 1
            row = active[0]
            bookings.append((line_id, product_ref_to_id[row["product_ref"]], int(row["quantity"]), row["due_date"]))
        bookings.sort()
        gold_bookings = sorted((row["line_id"], row["product_id"], row["quantity_units"], row["due_date"]) for row in gold["booked_lines"])
        contract_bookings = sorted((row["line_id"], row["product_id"], row["quantity_units"], row["due_date"]) for row in phase1_case["booked_lines"])
        assert bookings == gold_bookings == contract_bookings
        booked_total += sum(row[2] for row in bookings)

        # Draft buyer basket. A blank UOM is unusable until its explicit resolution.
        resolution_by_issue = {row["issue_id"]: row for row in files["resolutions.csv"]}
        basket = []
        for row in files["purchase_orders.csv"]:
            if row["status"] != "draft":
                continue
            product_id = product_ref_to_id[row["product_ref"]]
            uom = row["uom"]
            if not uom:
                assert row["source_row_id"] in issues["ISS-002"]["affected_source_row_ids"]
                uom = resolution_by_issue["ISS-002"]["chosen_value"]
            assert uom == "case"
            cases = int(row["quantity"])
            product = contract_products[product_id]
            units = cases * product["case_size"]
            value = Decimal(product["unit_cost_eur"]) * units
            basket.append((product_id, cases, units, value, row["expected_date"]))
        basket.sort()
        gold_basket = sorted(
            (row["product_id"], row["cases"], row["quantity_units"], Decimal(row["line_value_eur"]), gold["buyer_basket"]["arrival_date"])
            for row in gold["buyer_basket"]["lines"]
        )
        contract_basket = sorted(
            (
                row["product_id"],
                row["cases"],
                row["cases"] * contract_products[row["product_id"]]["case_size"],
                Decimal(contract_products[row["product_id"]]["unit_cost_eur"]) * row["cases"] * contract_products[row["product_id"]]["case_size"],
                phase1_case["buyer_basket"]["arrival_date"],
            )
            for row in phase1_case["buyer_basket"]["lines"]
        )
        assert basket == gold_basket == contract_basket

        supplier_id = phase1_case["supplier_id"]
        assert all(supplier_ref_to_id[row["supplier_ref"]] == supplier_id for row in files["purchase_orders.csv"] if row["status"] == "draft")
        merchandise = sum(row[3] for row in basket)
        cash = merchandise + Decimal(contract_suppliers[supplier_id]["delivery_charge_eur"])
        assert merchandise == Decimal(gold["buyer_basket"]["merchandise_eur"])
        assert cash == Decimal(gold["buyer_basket"]["immediate_cash_eur"])
        assert cash == Decimal(expected_cases[case_id]["buyer"]["immediate_cash_eur"])
        cash_total += cash

        # Existing partial purchase: ordered units minus linked receipt units,
        # with the supplier update supplying the outstanding ETA.
        incoming = []
        originals = [row for row in files["purchase_orders.csv"] if row["status"] == "partially_received"]
        for original in originals:
            product_id = product_ref_to_id[original["product_ref"]]
            product = contract_products[product_id]
            ordered_units = int(original["quantity"]) * product["case_size"]
            linked_receipts = [row for row in files["receipts.csv"] if row["purchase_order_ref"] == original["purchase_order_ref"] and row["line_ref"] == original["line_ref"]]
            received_units = sum(int(row["quantity"]) * product["case_size"] if row["uom"] == "case" else int(row["quantity"]) for row in linked_receipts)
            updates = [row for row in files["purchase_orders.csv"] if row["status"] == "outstanding_eta_update" and row["purchase_order_ref"] == original["purchase_order_ref"] and row["line_ref"] == original["line_ref"]]
            assert len(updates) == 1
            remaining = ordered_units - received_units
            assert remaining == int(updates[0]["quantity"]) * product["case_size"]
            incoming.append((product_id, remaining, updates[0]["expected_date"], contract_products[product_id]["incoming_expiry_date"]))
        incoming.sort()
        gold_incoming = sorted((row["product_id"], row["quantity_units"], row["arrival_date"], row["expiry_date"]) for row in gold["known_incoming"])
        contract_incoming = sorted((row["product_id"], row["quantity_units"], row["arrival_date"], row["expiry_date"]) for row in phase1_case["known_incoming"])
        assert incoming == gold_incoming == contract_incoming

    # Hard blockers are genuinely decision-critical before their resolutions.
    assert raw["positive_moq_composition"]["purchase_orders.csv"][0]["uom"] == ""
    assert any(row["minimum_merchandise_eur"] == "" for row in raw["no_change_control"]["supplier_terms.csv"])
    assert all(not case["unresolved_blockers"] for case in golden["cases"])

    return AuditResult(
        raw_files=file_count,
        source_rows=len(raw_ids),
        accounted_rows=len(accounted),
        issues=len(issues),
        cases=len(contract_cases),
        booked_units=booked_total,
        buyer_cash_eur=cash_total,
    )


if __name__ == "__main__":
    result = audit()
    print("PASS Phase 2 independent raw-to-golden reconciliation")
    print(f"raw_files={result.raw_files}")
    print(f"source_rows={result.source_rows}")
    print(f"accounted_rows={result.accounted_rows}")
    print(f"issues={result.issues}")
    print(f"cases={result.cases}")
    print(f"booked_units={result.booked_units}")
    print(f"buyer_cash_eur={result.buyer_cash_eur:.2f}")
