"""Authoritative behavioural tests for the frozen Stock Watch examples."""

from __future__ import annotations

from dataclasses import asdict
import csv
from io import StringIO
import json
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from src.stock_watch.config import MAX_CANDIDATES, PHASE1_DIR
from src.stock_watch.contracts import ImportContractError, ReconciliationBlocked
from src.stock_watch.engine import generate_plans, optimise, replay_plan
from src.stock_watch.importer import approve_issue, import_files, load_example, reconcile
from src.stock_watch.reporting import _safe, decision_payload, risk_csv, supplier_csv
from src.stock_watch.service import StockWatchService
from src.stock_watch.webapp import create_server


CASES = (("balanced_action", "SW-ISS-001"), ("unsafe_shelf_life", None), ("healthy_control", None))


def ready(case_id: str, issue_id: str | None):
    imported = load_example(case_id)
    return approve_issue(imported, issue_id) if issue_id else imported


class FrozenTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        expected = json.loads((PHASE1_DIR / "expected-results.json").read_text())
        cls.expected = {row["case_id"]: row for row in expected["cases"]}

    def test_all_three_cases_match_frozen_hand_truth(self):
        for case_id, issue_id in CASES:
            with self.subTest(case_id=case_id):
                decision = optimise(reconcile(ready(case_id, issue_id)))
                expected = self.expected[case_id]
                higher_current = next(row for row in decision.current.views if row.view_id == "higher")
                higher_selected = next(row for row in decision.selected.views if row.view_id == "higher")
                self.assertEqual(decision.verdict, expected["verdict"])
                self.assertEqual(decision.current.cash_eur, expected["current_cash_eur"])
                self.assertEqual(decision.selected.cash_eur, expected["selected_cash_eur"])
                self.assertEqual([(row["product_id"], row["cases"]) for row in decision.selected.lines], [tuple(row) for row in expected["selected_lines"]])
                self.assertEqual(higher_current.booked_on_time_units, expected["current_booked_on_time_units"])
                self.assertEqual(higher_selected.booked_on_time_units, expected["selected_booked_on_time_units"])
                self.assertEqual(higher_selected.booked_units, expected["booked_units"])
                self.assertEqual(higher_current.expired_units, expected["higher_current_expired_units"])
                self.assertEqual(higher_selected.expired_units, expected["higher_selected_expired_units"])
                self.assertFalse(higher_selected.accounting_errors)

    def test_selected_prediction_equals_fresh_replay_in_every_view(self):
        for case_id, issue_id in CASES:
            position = reconcile(ready(case_id, issue_id))
            decision = optimise(position)
            plan = [{key: row[key] for key in ("line_id", "product_id", "cases", "arrival_date", "expiry_date", "change_cutoff")} for row in decision.selected.lines]
            self.assertEqual(asdict(decision.selected), asdict(replay_plan(position, decision.selected.plan_id, plan)))

    def test_positive_case_orders_two_soup_cases_and_cancels_four_oat_cases(self):
        decision = optimise(reconcile(ready("balanced_action", "SW-ISS-001")))
        self.assertEqual([(row["product_id"], row["action"], row["current_cases"], row["selected_cases"]) for row in decision.actions], [
            ("PRD-OAT", "cancel", 4, 0), ("PRD-SOUP", "order_now", 0, 2)
        ])
        current_higher = next(row for row in decision.current.views if row.view_id == "higher")
        self.assertEqual((current_higher.run_outs[0]["product_id"], current_higher.run_outs[0]["date"]), ("PRD-SOUP", "2026-10-13"))

    def test_unsafe_case_keeps_four_cases_because_old_lot_is_ineligible(self):
        decision = optimise(reconcile(ready("unsafe_shelf_life", None)))
        three_case = next(row for row in decision.rejected if row.get("lines") and row["lines"][0]["cases"] == 3)
        self.assertTrue(any("higher: projected service falls by 12 units" in reason for reason in three_case["reasons"]))
        zero_case = next(row for row in decision.rejected if row.get("lines") and row["lines"][0]["cases"] == 0)
        self.assertTrue(any("booked deliveries fall short by 36 units" in reason for reason in zero_case["reasons"]))

    def test_healthy_control_has_no_expiry_and_keeps_two_cases(self):
        decision = optimise(reconcile(ready("healthy_control", None)))
        self.assertEqual(decision.verdict, "keep_plan")
        self.assertEqual(decision.at_risk_lots, ())
        self.assertEqual(decision.actions[0]["selected_cases"], 2)


class ImportAndBoundsTests(unittest.TestCase):
    def test_missing_unit_blocks_until_buyer_confirms_exact_conversion(self):
        imported = load_example("balanced_action")
        self.assertTrue(imported.blocked)
        with self.assertRaises(ReconciliationBlocked):
            reconcile(imported)
        position = reconcile(approve_issue(imported, "SW-ISS-001"))
        oat = next(row for row in position["lots"] if row["product_id"] == "PRD-OAT")
        self.assertEqual(oat["quantity_units"], 60)

    def test_aliases_and_purchase_amendment_preserve_source_rows(self):
        position = reconcile(ready("balanced_action", "SW-ISS-001"))
        purchase = position["purchases"][0]
        self.assertEqual((purchase["product_id"], purchase["cases"]), ("PRD-OAT", 4))
        self.assertEqual(purchase["source_row_ids"], ["BAL-PO-001", "BAL-PO-002"])

    def test_import_is_deterministic_and_rejects_schema_or_file_drift(self):
        first = ready("healthy_control", None)
        second = import_files(first.files)
        self.assertEqual(first.input_hash, second.input_hash)
        missing = dict(first.files)
        missing.pop("stock_lots.csv")
        with self.assertRaisesRegex(ImportContractError, "seven named CSVs"):
            import_files(missing)
        drift = dict(first.files)
        drift["products.csv"] = drift["products.csv"].replace("product_name", "renamed", 1)
        with self.assertRaisesRegex(ImportContractError, "frozen schema"):
            import_files(drift)

    def test_future_known_demand_is_rejected(self):
        imported = ready("healthy_control", None)
        files = dict(imported.files)
        files["demand_views.csv"] = files["demand_views.csv"].replace("2026-10-05T08:00:00+02:00", "2026-10-06T08:00:00+02:00", 1)
        with self.assertRaisesRegex(ImportContractError, "Future-known"):
            reconcile(import_files(files))

    def test_search_is_deterministic_bounded_and_reports_physical_work(self):
        for case_id, issue_id in CASES:
            position = reconcile(ready(case_id, issue_id))
            self.assertEqual(generate_plans(position), generate_plans(position))
            decision = optimise(position)
            self.assertLessEqual(decision.search_report["generated_candidates"], MAX_CANDIDATES)
            self.assertEqual(decision.search_report["preflight_rejected"] + decision.search_report["physically_replayed"], decision.search_report["generated_candidates"])
            self.assertGreaterEqual(decision.search_report["survivors"], 1)


class ReportingAndServiceTests(unittest.TestCase):
    def test_payload_and_exports_trace_to_same_decision(self):
        decision = optimise(reconcile(ready("balanced_action", "SW-ISS-001")))
        payload = decision_payload(decision)
        order_rows = list(csv.DictReader(StringIO(supplier_csv(decision))))
        risk_rows = list(csv.DictReader(StringIO(risk_csv(decision))))
        self.assertEqual(payload["comparison"]["cash_change_eur"], "-24.00")
        self.assertEqual({row["decision_hash"] for row in order_rows}, {decision.decision_hash})
        self.assertEqual(sum(int(row["projected_units"]) for row in risk_rows), 24)
        self.assertTrue(all(row["synthetic_example"] == "true" for row in order_rows + risk_rows))

    def test_formula_like_csv_values_are_neutralized(self):
        for value in ("=SUM(A1:A2)", "+1", "-2", "@cmd"):
            self.assertTrue(_safe(value).startswith("'"))

    def test_sessions_are_isolated_and_blocked_exports_are_refused(self):
        service = StockWatchService()
        balanced = service.create_example("balanced_action")
        control = service.create_example("healthy_control")
        self.assertNotEqual(balanced["session_id"], control["session_id"])
        self.assertTrue(balanced["blocked"])
        with self.assertRaises(ReconciliationBlocked):
            service.export_order(balanced["session_id"])
        ready_payload = service.resolve(balanced["session_id"], "SW-ISS-001")
        self.assertEqual(ready_payload["decision"]["verdict"], "change_plan")
        self.assertEqual(service.view(control["session_id"])["decision"]["verdict"], "keep_plan")


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def request(self, path: str, payload=None, method: str | None = None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=3) as response:
            body = response.read()
            return response, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body

    def test_health_static_examples_and_security_headers(self):
        response, health = self.request("/api/health")
        self.assertEqual(health["product"], "stock-watch")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        _, page = self.request("/")
        self.assertIn(b"What will run out", page)
        _, examples = self.request("/api/examples")
        self.assertEqual(len(examples), 3)

    def test_complete_positive_flow_and_two_exports(self):
        _, session = self.request("/api/sessions/example", {"case_id": "balanced_action"})
        self.assertTrue(session["blocked"])
        _, resolved = self.request(f"/api/sessions/{session['session_id']}/resolve", {"issue_id": "SW-ISS-001"})
        self.assertEqual(resolved["decision"]["selected"]["cash_eur"], "58.00")
        for suffix in ("export-order", "export-risk"):
            response, body = self.request(f"/api/sessions/{session['session_id']}/{suffix}")
            self.assertIn("attachment", response.headers["Content-Disposition"])
            self.assertIn(b"decision_hash", body)


if __name__ == "__main__":
    unittest.main()
