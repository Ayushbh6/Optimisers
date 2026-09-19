"""Authoritative tests for the frozen Supplier Basket Review showcase."""

from __future__ import annotations

from dataclasses import asdict
import csv
from io import StringIO
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.supplier_basket.config import EXPECTED_FILES, PHASE1_DIR, PHASE2_DIR, RAW_DIR
from src.supplier_basket.contracts import ImportContractError, ReconciliationBlocked
from src.supplier_basket.importer import approve_issue, import_files, load_example
from src.supplier_basket.optimizer import MAX_ALTERNATIVES, generate_candidates, optimise
from src.supplier_basket.reconciliation import stable_reconcile
from src.supplier_basket.replay import buyer_basket, replay, validate_basket
from src.supplier_basket.reporting import _safe_cell, decision_payload, supplier_csv
from src.supplier_basket.service import SupplierBasketService
from src.supplier_basket.webapp import create_server


CASES = (
    ("positive_moq_composition", "ISS-002"),
    ("unsafe_cheaper_delivery_loss", None),
    ("no_change_control", "ISS-005"),
)


def ready_import(case_id: str, issue_id: str | None):
    imported = load_example(case_id)
    return approve_issue(imported, issue_id) if issue_id else imported


class ImportAndReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads((PHASE2_DIR / "golden" / "normalized-ledger.json").read_text())
        cls.golden_cases = {row["case_id"]: row for row in cls.golden["cases"]}

    def test_all_cases_exactly_match_frozen_golden_ledger(self):
        for case_id, issue_id in CASES:
            with self.subTest(case_id=case_id):
                ledger = stable_reconcile(ready_import(case_id, issue_id))
                self.assertEqual(ledger["case"], self.golden_cases[case_id])

    def test_reimport_and_reconciliation_are_deterministic(self):
        imported = ready_import("positive_moq_composition", "ISS-002")
        files = dict(imported.files)
        second = import_files(files, approved_issue_ids={"ISS-002"})
        self.assertEqual(imported.input_hash, second.input_hash)
        self.assertEqual(stable_reconcile(imported), stable_reconcile(second))

    def test_confirmation_and_hard_blocker_prevent_planning(self):
        for case_id, issue_id in (
            ("positive_moq_composition", "ISS-002"),
            ("no_change_control", "ISS-005"),
        ):
            imported = load_example(case_id)
            self.assertTrue(imported.blocked)
            with self.assertRaises(ReconciliationBlocked):
                stable_reconcile(imported)
            self.assertFalse(approve_issue(imported, issue_id).blocked)

    def test_provenance_survives_alias_amendment_and_partial_receipt(self):
        positive = stable_reconcile(ready_import("positive_moq_composition", "ISS-002"))["case"]
        self.assertEqual(positive["opening_stock"][1]["source_row_ids"], ["POS-STK-008", "POS-REC-008"])
        self.assertEqual(
            positive["known_incoming"][0]["source_row_ids"],
            ["POS-PO-OLD-101", "POS-PO-OLD-101-ETA", "POS-REC-008"],
        )
        unsafe = stable_reconcile(load_example("unsafe_cheaper_delivery_loss"))["case"]
        amended = next(row for row in unsafe["booked_lines"] if row["line_id"] == "UNS-CO-002")
        self.assertEqual(amended["quantity_units"], 24)
        self.assertEqual(amended["source_row_ids"], ["UNS-CO-ROW-002-A1", "UNS-CO-ROW-002-A2"])

    def test_upload_contract_rejects_missing_files_and_duplicate_ids(self):
        source = load_example("unsafe_cheaper_delivery_loss").files
        missing = dict(source)
        missing.pop("receipts.csv")
        with self.assertRaisesRegex(ImportContractError, "Expected seven named CSVs"):
            import_files(missing)
        duplicate = dict(source)
        duplicate["products.csv"] = duplicate["products.csv"].replace("UNS-PROD-005", "UNS-PROD-004")
        with self.assertRaisesRegex(ImportContractError, "globally unique"):
            import_files(duplicate)

    def test_upload_contract_rejects_schema_drift(self):
        files = dict(load_example("unsafe_cheaper_delivery_loss").files)
        files["products.csv"] = files["products.csv"].replace("description,", "renamed_description,", 1)
        with self.assertRaisesRegex(ImportContractError, "frozen schema"):
            import_files(files)

    def test_future_known_record_and_out_of_date_cost_are_rejected(self):
        files = dict(load_example("unsafe_cheaper_delivery_loss").files)
        files["customer_orders.csv"] = files["customer_orders.csv"].replace(
            "2026-09-14T11:00:00+02:00", "2026-09-19T11:00:00+02:00", 1
        )
        with self.assertRaisesRegex(ImportContractError, "Future-known record"):
            stable_reconcile(import_files(files))
        files = dict(load_example("unsafe_cheaper_delivery_loss").files)
        files["products.csv"] = files["products.csv"].replace("2026-09-01,2026-12-31", "2025-01-01,2025-12-31", 1)
        with self.assertRaisesRegex(ImportContractError, "Product cost is not effective"):
            stable_reconcile(import_files(files))


class ExactDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        expected = json.loads((PHASE1_DIR / "expected-results.json").read_text())
        cls.expected = {row["case_id"]: row for row in expected["cases"]}

    def decision(self, case_id: str, issue_id: str | None):
        return optimise(stable_reconcile(ready_import(case_id, issue_id)))

    def test_all_three_verdicts_and_physical_totals_match_hand_truth(self):
        verdicts = {
            "positive_moq_composition": "accept_proposed",
            "unsafe_cheaper_delivery_loss": "retain_buyer",
            "no_change_control": "retain_buyer",
        }
        selected_key = {
            "positive_moq_composition": "proposed",
            "unsafe_cheaper_delivery_loss": "buyer",
            "no_change_control": "buyer",
        }
        for case_id, issue_id in CASES:
            with self.subTest(case_id=case_id):
                decision = self.decision(case_id, issue_id)
                truth = self.expected[case_id]
                selected_truth = truth[selected_key[case_id]]
                self.assertEqual(decision.verdict, verdicts[case_id])
                self.assertEqual(decision.selected.immediate_cash_eur, selected_truth["immediate_cash_eur"])
                self.assertEqual(decision.selected.on_time_units, selected_truth["on_time_units"])
                self.assertEqual(decision.selected.complete_lines, selected_truth["complete_lines"])
                self.assertEqual(decision.selected.expired_units, selected_truth["expired_units"])
                self.assertEqual(decision.selected.sum_28_daily_exposure_eur, selected_truth["sum_28_daily_exposure_eur"])
                self.assertEqual(decision.selected.ending_stock_plus_commitments_eur, selected_truth["ending_stock_plus_commitments_eur"])
                self.assertFalse(decision.selected.accounting_errors)

    def test_selected_prediction_exactly_equals_fresh_physical_replay(self):
        for case_id, issue_id in CASES:
            ledger = stable_reconcile(ready_import(case_id, issue_id))
            decision = optimise(ledger)
            basket = [{"product_id": row["product_id"], "cases": row["cases"]} for row in decision.selected.lines]
            fresh = replay(ledger["case"], decision.selected.basket_id, basket)
            self.assertEqual(asdict(fresh), asdict(decision.selected))

    def test_search_is_bounded_and_reports_actual_work(self):
        for case_id, issue_id in CASES:
            decision = self.decision(case_id, issue_id)
            report = decision.search_report
            self.assertLessEqual(len(decision.candidates), MAX_ALTERNATIVES)
            self.assertEqual(report["generated_alternatives"], len(decision.candidates))
            self.assertEqual(
                report["rejected_preflight"] + report["physically_replayed"],
                report["generated_alternatives"],
            )
            self.assertGreaterEqual(report["elapsed_ms"], 0)

    def test_positive_candidate_is_exact_frozen_minimum_repair(self):
        decision = self.decision("positive_moq_composition", "ISS-002")
        self.assertEqual(len(decision.candidates), 9)
        self.assertEqual(decision.selected.basket_id, "POS-RM-003-REPAIR-001")
        self.assertEqual(
            [(row["product_id"], row["cases"]) for row in decision.selected.lines],
            [("PRD-001", 8), ("PRD-002", 2)],
        )
        self.assertEqual(decision.buyer.immediate_cash_eur, "620.00")
        self.assertEqual(decision.selected.immediate_cash_eur, "524.00")

    def test_unsafe_cheaper_edit_is_rejected_for_exact_delivery_loss(self):
        decision = self.decision("unsafe_cheaper_delivery_loss", None)
        challenged = next(row for row in decision.candidates if row.candidate_id == "UNS-RED-004-REPAIR-006")
        self.assertEqual(challenged.replay.immediate_cash_eur, "183.00")
        self.assertEqual(challenged.replay.on_time_units, 42)
        self.assertIn("Booked delivery regression: 12 fewer on-time units", challenged.rejection_reasons)
        failure = challenged.replay.delivery_failures[0]
        self.assertEqual((failure["line_id"], failure["due_date"], failure["undelivered_units"]), ("UNS-CO-002", "2026-09-24", 12))

    def test_no_change_control_exhausts_frozen_twelve_candidates(self):
        decision = self.decision("no_change_control", "ISS-005")
        self.assertEqual(len(decision.candidates), 12)
        self.assertFalse(any(row.decision_status == "survivor" for row in decision.candidates))

    def test_preflight_enforces_cases_minimum_budget_capacity_and_dates(self):
        ledger = stable_reconcile(ready_import("positive_moq_composition", "ISS-002"))["case"]
        self.assertTrue(validate_basket(ledger, [{"product_id": "PRD-001", "cases": 0}]))
        over_budget = [{"product_id": "PRD-001", "cases": 21}]
        errors = validate_basket(ledger, over_budget)
        self.assertTrue(any("allowance" in error for error in errors))
        self.assertTrue(any("Receipt exceeds" in error for error in errors))
        wrong_arrival = json.loads(json.dumps(ledger))
        wrong_arrival["buyer_basket"]["arrival_date"] = "2026-09-23"
        self.assertTrue(any("Expected arrival" in error for error in validate_basket(wrong_arrival, buyer_basket(ledger))))

    def test_candidate_order_and_decision_are_deterministic(self):
        ledger = stable_reconcile(ready_import("positive_moq_composition", "ISS-002"))
        first = generate_candidates(ledger["case"])
        second = generate_candidates(ledger["case"])
        self.assertEqual(first, second)
        self.assertEqual(optimise(ledger).decision_hash, optimise(ledger).decision_hash)


class ExplanationAndServiceTests(unittest.TestCase):
    def test_payload_and_export_share_selected_decision_totals(self):
        decision = optimise(stable_reconcile(ready_import("positive_moq_composition", "ISS-002")))
        payload = decision_payload(decision)
        exported = list(csv.DictReader(StringIO(supplier_csv(decision))))
        self.assertEqual(sum(float(row["line_value_eur"]) for row in exported) + float(payload["supplier"]["delivery_charge_eur"]), 524.0)
        self.assertEqual({row["decision_hash"] for row in exported}, {payload["decision_hash"]})
        self.assertTrue(all(row["synthetic_case_study"] == "true" for row in exported))
        self.assertEqual(payload["comparison"]["cash_change_eur"], "-96.00")

    def test_spreadsheet_formula_prefixes_are_neutralized(self):
        for value in ("=SUM(A1:A2)", "+1", "-2", "@cmd"):
            self.assertTrue(_safe_cell(value).startswith("'"))
        self.assertEqual(_safe_cell("ordinary"), "ordinary")

    def test_service_sessions_are_isolated_and_blocked_export_is_refused(self):
        service = SupplierBasketService()
        positive = service.create_example("positive_moq_composition")
        unsafe = service.create_example("unsafe_cheaper_delivery_loss")
        self.assertNotEqual(positive["session_id"], unsafe["session_id"])
        self.assertTrue(positive["blocked"])
        with self.assertRaises(ReconciliationBlocked):
            service.export(positive["session_id"])
        ready = service.resolve(positive["session_id"], "ISS-002")
        self.assertFalse(ready["blocked"])
        self.assertEqual(ready["decision"]["verdict"], "accept_proposed")
        self.assertEqual(service.view(unsafe["session_id"])["decision"]["verdict"], "retain_buyer")
        service.delete(positive["session_id"])
        with self.assertRaises(KeyError):
            service.view(positive["session_id"])


class HttpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path: str, payload=None, method: str | None = None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base + path, data=data, headers={"Content-Type": "application/json"}, method=method)
        with urlopen(request, timeout=3) as response:
            body = response.read()
            return response, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body

    def test_health_static_security_headers_and_examples(self):
        response, health = self.request("/api/health")
        self.assertEqual(health["status"], "ready")
        self.assertTrue(health["synthetic"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        response, page = self.request("/")
        self.assertIn(b"Weekly Order Check", page)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        _, examples = self.request("/api/examples")
        self.assertEqual(len(examples), 3)

    def test_complete_positive_api_flow_and_export(self):
        _, session = self.request("/api/sessions/example", {"case_id": "positive_moq_composition"})
        self.assertTrue(session["blocked"])
        _, ready = self.request(f"/api/sessions/{session['session_id']}/resolve", {"issue_id": "ISS-002"})
        self.assertEqual(ready["decision"]["selected"]["immediate_cash_eur"], "524.00")
        response, body = self.request(f"/api/sessions/{session['session_id']}/export")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn(b"decision_hash", body)
        _, deleted = self.request(f"/api/sessions/{session['session_id']}", method="DELETE")
        self.assertTrue(deleted["deleted"])

    def test_unknown_case_and_incomplete_upload_return_clear_errors(self):
        with self.assertRaises(HTTPError) as unknown:
            self.request("/api/sessions/example", {"case_id": "missing"})
        self.assertEqual(unknown.exception.code, 400)
        with self.assertRaises(HTTPError) as incomplete:
            self.request("/api/sessions/upload", {"files": {"products.csv": "x"}})
        self.assertEqual(incomplete.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
