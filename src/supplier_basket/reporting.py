"""Buyer-readable decision payloads and supplier-ready CSV exports."""

from __future__ import annotations

import csv
from dataclasses import asdict
from decimal import Decimal
from io import StringIO
from typing import Any

from .contracts import DecisionResult
from .reconciliation import load_contract


def _safe_cell(value: Any) -> str:
    """Prevent spreadsheet formula execution in exported text cells."""
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _change(before: str, after: str) -> str:
    return f"{Decimal(after) - Decimal(before):.2f}"


def decision_payload(decision: DecisionResult) -> dict[str, Any]:
    """Build the single source of truth consumed by UI and exports."""
    contract = load_contract()
    products = {row["product_id"]: row for row in contract["products"]}
    suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    case_contract = next(row for row in contract["cases"] if row["case_id"] == decision.case_id)
    supplier = suppliers[case_contract["supplier_id"]]

    def replay_payload(result) -> dict[str, Any]:
        payload = asdict(result)
        payload["lines"] = [
            {
                **line,
                "product_name": products[line["product_id"]]["name"],
                "base_uom": products[line["product_id"]]["base_uom"],
                "case_size": products[line["product_id"]]["case_size"],
            }
            for line in payload["lines"]
        ]
        return payload
    changes = []
    for row in decision.product_changes:
        product = products[row["product_id"]]
        changes.append({
            **row,
            "product_name": product["name"],
            "case_size": product["case_size"],
            "unit": product["base_uom"],
        })
    rejected = []
    for row in decision.candidates:
        if row.decision_status == "survivor":
            continue
        replay = asdict(row.replay) if row.replay else None
        rejected.append({
            "candidate_id": row.candidate_id,
            "generation_reason": row.generation_reason,
            "status": row.decision_status,
            "reasons": list(row.rejection_reasons),
            "cash_eur": replay["immediate_cash_eur"] if replay else None,
            "delivery_failures": replay["delivery_failures"] if replay else [],
        })
    return {
        "schema_version": "1.0",
        "case_id": decision.case_id,
        "input_hash": decision.input_hash,
        "decision_hash": decision.decision_hash,
        "synthetic_case_study": True,
        "verdict": decision.verdict,
        "summary": decision.summary,
        "supplier": {
            "supplier_id": supplier["supplier_id"],
            "name": supplier["name"],
            "order_day": supplier["order_weekday"].title(),
            "delivery_charge_eur": supplier["delivery_charge_eur"],
        },
        "buyer": replay_payload(decision.buyer),
        "selected": replay_payload(decision.selected),
        "comparison": {
            "cash_change_eur": _change(decision.buyer.immediate_cash_eur, decision.selected.immediate_cash_eur),
            "average_exposure_change_eur": _change(decision.buyer.average_daily_exposure_eur, decision.selected.average_daily_exposure_eur),
            "ending_stock_plus_commitments_change_eur": _change(decision.buyer.ending_stock_plus_commitments_eur, decision.selected.ending_stock_plus_commitments_eur),
            "on_time_units_change": decision.selected.on_time_units - decision.buyer.on_time_units,
            "expired_units_change": decision.selected.expired_units - decision.buyer.expired_units,
        },
        "product_changes": changes,
        "delivery_risks": list(decision.risks),
        "operational_consequences": {
            "expected_arrival": decision.selected.lines[0]["expected_arrival"] if decision.selected.lines else None,
            "booked_units_protected": decision.selected.on_time_units,
            "booked_units_total": decision.selected.booked_units,
            "ending_stock_plus_commitments_eur": decision.selected.ending_stock_plus_commitments_eur,
            "ending_change_eur": _change(decision.buyer.ending_stock_plus_commitments_eur, decision.selected.ending_stock_plus_commitments_eur),
            "expired_units": decision.selected.expired_units,
        },
        "rejected_alternatives": rejected,
        "assumptions": list(decision.assumptions),
        "search_report": decision.search_report,
        "buyer_action": "Send the revised supplier draft" if decision.verdict == "accept_proposed" else "Keep and send the buyer draft",
        "claim_boundary": "Synthetic case-study result. This is not a realised client saving.",
    }


def supplier_csv(decision: DecisionResult) -> str:
    """Render the selected basket as an auditable supplier-ready draft."""
    payload = decision_payload(decision)
    contract = load_contract()
    products = {row["product_id"]: row for row in contract["products"]}
    output = StringIO(newline="")
    fields = [
        "supplier_id",
        "supplier_name",
        "product_id",
        "product_name",
        "cases",
        "units",
        "base_uom",
        "unit_cost_eur",
        "line_value_eur",
        "expected_arrival",
        "decision_hash",
        "synthetic_case_study",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for line in decision.selected.lines:
        product = products[line["product_id"]]
        writer.writerow({
            "supplier_id": _safe_cell(payload["supplier"]["supplier_id"]),
            "supplier_name": _safe_cell(payload["supplier"]["name"]),
            "product_id": _safe_cell(line["product_id"]),
            "product_name": _safe_cell(product["name"]),
            "cases": line["cases"],
            "units": line["quantity_units"],
            "base_uom": _safe_cell(product["base_uom"]),
            "unit_cost_eur": line["unit_cost_eur"],
            "line_value_eur": line["line_value_eur"],
            "expected_arrival": line["expected_arrival"],
            "decision_hash": decision.decision_hash,
            "synthetic_case_study": "true",
        })
    return output.getvalue()
