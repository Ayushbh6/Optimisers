"""Buyer-facing payloads and safe CSV exports."""

from __future__ import annotations

from dataclasses import asdict
import csv
from io import StringIO

from .contracts import DecisionResult


def _safe(value: object) -> str:
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def decision_payload(decision: DecisionResult) -> dict:
    """Return one traceable object used by the browser and exports."""
    payload = asdict(decision)
    current_views = {row["view_id"]: row for row in payload["current"]["views"]}
    selected_views = {row["view_id"]: row for row in payload["selected"]["views"]}
    current_higher, selected_higher = current_views["higher"], selected_views["higher"]
    payload["comparison"] = {
        "cash_change_eur": f"{float(payload['selected']['cash_eur']) - float(payload['current']['cash_eur']):.2f}",
        "booked_change_units": selected_higher["booked_on_time_units"] - current_higher["booked_on_time_units"],
        "expiry_change_units": selected_higher["expired_units"] - current_higher["expired_units"],
        "ending_stock_change_eur": f"{float(selected_higher['ending_stock_eur']) - float(current_higher['ending_stock_eur']):.2f}",
    }
    payload["claim_boundary"] = "Synthetic example. Projected outcomes are not realised savings or guaranteed waste prevention."
    return payload


def supplier_csv(decision: DecisionResult) -> str:
    """Create the selected weekly supplier instruction as CSV."""
    output = StringIO()
    fields = ("action", "product_id", "product_name", "current_cases", "recommended_cases", "arrival_date", "line_value_eur", "decision_hash", "synthetic_example")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    selected = {row["product_id"]: row for row in decision.selected.lines}
    for action in decision.actions:
        line = selected.get(action["product_id"], {})
        writer.writerow({
            "action": _safe(action["action"]), "product_id": _safe(action["product_id"]), "product_name": _safe(action["product_name"]),
            "current_cases": action["current_cases"], "recommended_cases": action["selected_cases"],
            "arrival_date": line.get("arrival_date", ""), "line_value_eur": line.get("line_value_eur", "0.00"),
            "decision_hash": decision.decision_hash, "synthetic_example": "true",
        })
    return output.getvalue()


def risk_csv(decision: DecisionResult) -> str:
    """Create the selected plan's residual lot-risk list."""
    output = StringIO()
    fields = ("product_id", "product_name", "lot_id", "projected_expiry_date", "projected_units", "demand_view", "decision_hash", "synthetic_example")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in decision.at_risk_lots:
        writer.writerow({
            "product_id": _safe(row["product_id"]), "product_name": _safe(row["product_name"]), "lot_id": _safe(row["lot_id"]),
            "projected_expiry_date": row["date"], "projected_units": row["quantity_units"], "demand_view": "higher",
            "decision_hash": decision.decision_hash, "synthetic_example": "true",
        })
    return output.getvalue()
