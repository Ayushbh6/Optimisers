"""Bounded purchase actions judged by exact lot-level physical replay."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
import hashlib
from itertools import product
import json
from time import perf_counter
from typing import Any

from .config import MAX_CANDIDATES, REQUIRED_VIEWS
from .contracts import DecisionResult, PlanResult, ViewResult


def _money(value: Decimal) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def current_plan(position: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the buyer's current open purchase lines."""
    return [
        {
            "line_id": row["line_id"], "product_id": row["product_id"], "cases": row["cases"],
            "arrival_date": row["expected_arrival"], "expiry_date": row["expiry_date"], "change_cutoff": row["change_cutoff"],
        }
        for row in position["purchases"]
    ]


def generate_plans(position: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Generate a deterministic, explicitly bounded whole-case neighborhood."""
    supplier = position["supplier"]
    review = date.fromisoformat(supplier["review_date"])
    existing = {row["product_id"]: row for row in position["purchases"]}
    dimensions: list[tuple[str, range]] = []
    for product_id in sorted(position["products"]):
        product_row = position["products"][product_id]
        if product_id in existing:
            dimensions.append((product_id, range(existing[product_id]["cases"] + 1)))
        elif product_row["max_new_cases"]:
            dimensions.append((product_id, range(product_row["max_new_cases"] + 1)))
    plans: list[list[dict[str, Any]]] = []
    for quantities in product(*(choices for _, choices in dimensions)):
        lines = []
        for (product_id, _), cases in zip(dimensions, quantities, strict=True):
            existing_row = existing.get(product_id)
            product_row = position["products"][product_id]
            lines.append({
                "line_id": existing_row["line_id"] if existing_row else f"NEW-{product_id}",
                "product_id": product_id,
                "cases": cases,
                "arrival_date": existing_row["expected_arrival"] if existing_row else (review + timedelta(days=supplier["lead_days"])).isoformat(),
                "expiry_date": existing_row["expiry_date"] if existing_row else product_row["new_receipt_expiry_date"],
                "change_cutoff": existing_row["change_cutoff"] if existing_row else supplier["review_date"],
            })
        plans.append(lines)
        if len(plans) > MAX_CANDIDATES:
            raise ValueError(f"Search exceeded the frozen {MAX_CANDIDATES}-plan limit")
    return plans


def validate_plan(position: dict[str, Any], plan: list[dict[str, Any]]) -> list[str]:
    """Enforce dated supplier terms, case quantities, budget and receipt capacity."""
    supplier = position["supplier"]
    review = date.fromisoformat(supplier["review_date"])
    errors: list[str] = []
    if review.strftime("%A").upper() != supplier["order_weekday"]:
        errors.append(f"Orders may be changed only on {supplier['order_weekday'].title()}")
    if not (date.fromisoformat(supplier["effective_from"]) <= review <= date.fromisoformat(supplier["effective_to"])):
        errors.append("Supplier terms are not effective on the review date")
    current = {row["product_id"]: row for row in current_plan(position)}
    merchandise = Decimal("0")
    receipts: dict[str, int] = defaultdict(int)
    for line in plan:
        cases = line["cases"]
        if type(cases) is not int or cases < 0:
            errors.append(f"Whole non-negative cases required for {line['product_id']}")
            continue
        product_row = position["products"][line["product_id"]]
        if line["product_id"] in current and cases != current[line["product_id"]]["cases"] and review > date.fromisoformat(line["change_cutoff"]):
            errors.append(f"Change cut-off passed for {line['line_id']}")
        units = cases * product_row["case_size"]
        merchandise += Decimal(product_row["unit_cost_eur"]) * units
        receipts[line["arrival_date"]] += units
    charge = Decimal(supplier["delivery_charge_eur"]) if any(line["cases"] for line in plan) else Decimal("0")
    if merchandise + charge > Decimal(supplier["budget_eur"]):
        errors.append(f"Plan exceeds the €{supplier['budget_eur']} weekly budget")
    if any(units > supplier["receipt_capacity_units"] for units in receipts.values()):
        errors.append("Plan exceeds daily receipt capacity")
    return errors


def _replay_view(position: dict[str, Any], plan: list[dict[str, Any]], view_id: str) -> ViewResult:
    products = position["products"]
    start = date.fromisoformat(position["supplier"]["review_date"])
    days = [start + timedelta(days=offset) for offset in range(28)]
    lots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in position["lots"]:
        if row["stock_status"] == "AVAILABLE":
            lots[row["product_id"]].append({"lot_id": row["lot_id"], "quantity": row["quantity_units"], "expiry": date.fromisoformat(row["expiry_date"])})
    receipts: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for line in plan:
        if not line["cases"]:
            continue
        product_row = products[line["product_id"]]
        receipts[date.fromisoformat(line["arrival_date"])].append({
            "lot_id": f"{line['line_id']}-LOT", "product_id": line["product_id"],
            "quantity": line["cases"] * product_row["case_size"], "expiry": date.fromisoformat(line["expiry_date"]),
        })
    events: dict[date, list[dict[str, Any]]] = defaultdict(list)
    booked_total = 0
    for row in position["booked_orders"]:
        events[date.fromisoformat(row["due_date"])].append({**row, "kind": "booked", "event_id": row["line_id"]})
        booked_total += row["quantity_units"]
    projected_total = 0
    for row in position["demand_views"][view_id]:
        events[date.fromisoformat(row["due_date"])].append({**row, "kind": "projected"})
        projected_total += row["quantity_units"]
    booked_fulfilled = projected_fulfilled = expired_total = 0
    expired_cost = Decimal("0")
    run_outs: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    errors: list[str] = []
    for day in days:
        opening = {pid: sum(lot["quantity"] for lot in values) for pid, values in lots.items()}
        received: dict[str, int] = defaultdict(int)
        shipped: dict[str, int] = defaultdict(int)
        expired: dict[str, int] = defaultdict(int)
        expired_lots: list[dict[str, Any]] = []
        for pid, values in lots.items():
            for lot in values:
                if lot["quantity"] and lot["expiry"] < day:
                    quantity = lot["quantity"]
                    lot["quantity"] = 0
                    expired[pid] += quantity
                    expired_total += quantity
                    expired_cost += Decimal(products[pid]["unit_cost_eur"]) * quantity
                    expired_lots.append({"lot_id": lot["lot_id"], "product_id": pid, "quantity_units": quantity})
        for receipt in receipts.get(day, []):
            lots[receipt["product_id"]].append({"lot_id": receipt["lot_id"], "quantity": receipt["quantity"], "expiry": receipt["expiry"]})
            received[receipt["product_id"]] += receipt["quantity"]
        for event in sorted(events.get(day, []), key=lambda row: (row["kind"] != "booked", row["event_id"])):
            need = event["quantity_units"]
            fulfilled = 0
            for lot in sorted(lots[event["product_id"]], key=lambda row: (row["expiry"], row["lot_id"])):
                if (lot["expiry"] - day).days < event["min_shelf_life_days"]:
                    continue
                quantity = min(need, lot["quantity"])
                lot["quantity"] -= quantity
                need -= quantity
                fulfilled += quantity
                shipped[event["product_id"]] += quantity
                if not need:
                    break
            if event["kind"] == "booked":
                booked_fulfilled += fulfilled
            else:
                projected_fulfilled += fulfilled
            if need:
                run_outs.append({
                    "product_id": event["product_id"], "date": day.isoformat(), "event_id": event["event_id"],
                    "kind": event["kind"], "missing_units": need,
                })
        closing = {pid: sum(lot["quantity"] for lot in values) for pid, values in lots.items()}
        for pid in set(opening) | set(received) | set(shipped) | set(expired) | set(closing):
            expected = opening.get(pid, 0) + received.get(pid, 0) - shipped.get(pid, 0) - expired.get(pid, 0)
            if expected != closing.get(pid, 0):
                errors.append(f"{day}:{pid}: expected {expected}, got {closing.get(pid, 0)}")
        stock_value = sum(Decimal(products[pid]["unit_cost_eur"]) * lot["quantity"] for pid, values in lots.items() for lot in values)
        ledger.append({
            "date": day.isoformat(), "received_units": sum(received.values()), "dispatched_units": sum(shipped.values()),
            "expired_units": sum(expired.values()), "expired_lots": expired_lots, "closing_stock_units": sum(closing.values()),
            "closing_stock_eur": _money(stock_value),
        })
    ending_units = sum(lot["quantity"] for values in lots.values() for lot in values)
    ending_value = sum(Decimal(products[pid]["unit_cost_eur"]) * lot["quantity"] for pid, values in lots.items() for lot in values)
    return ViewResult(
        view_id=view_id, booked_units=booked_total, booked_on_time_units=booked_fulfilled,
        projected_units=projected_total, projected_fulfilled_units=projected_fulfilled,
        expired_units=expired_total, expired_cost_eur=_money(expired_cost), ending_stock_units=ending_units,
        ending_stock_eur=_money(ending_value), run_outs=tuple(run_outs), daily_ledger=tuple(ledger), accounting_errors=tuple(errors),
    )


def replay_plan(position: dict[str, Any], plan_id: str, plan: list[dict[str, Any]]) -> PlanResult:
    """Replay one feasible plan through every frozen demand view."""
    errors = validate_plan(position, plan)
    if errors:
        raise ValueError("; ".join(errors))
    lines = []
    merchandise = Decimal("0")
    for line in sorted(plan, key=lambda row: row["product_id"]):
        product_row = position["products"][line["product_id"]]
        units = line["cases"] * product_row["case_size"]
        value = Decimal(product_row["unit_cost_eur"]) * units
        merchandise += value
        lines.append({
            **line, "product_name": product_row["product_name"], "case_size": product_row["case_size"],
            "quantity_units": units, "unit_cost_eur": product_row["unit_cost_eur"], "line_value_eur": _money(value),
        })
    delivery = Decimal(position["supplier"]["delivery_charge_eur"]) if any(row["cases"] for row in plan) else Decimal("0")
    return PlanResult(
        plan_id=plan_id, lines=tuple(lines), merchandise_eur=_money(merchandise), delivery_charge_eur=_money(delivery),
        cash_eur=_money(merchandise + delivery), views=tuple(_replay_view(position, plan, view) for view in REQUIRED_VIEWS),
    )


def _view_map(result: PlanResult) -> dict[str, ViewResult]:
    return {view.view_id: view for view in result.views}


def _rejections(current: PlanResult, candidate: PlanResult) -> list[str]:
    baseline = _view_map(current)
    reasons: list[str] = []
    for view in candidate.views:
        if view.booked_on_time_units < view.booked_units:
            reasons.append(f"{view.view_id}: booked deliveries fall short by {view.booked_units - view.booked_on_time_units} units")
        if view.projected_fulfilled_units < baseline[view.view_id].projected_fulfilled_units:
            reasons.append(f"{view.view_id}: projected service falls by {baseline[view.view_id].projected_fulfilled_units - view.projected_fulfilled_units} units")
        if view.expired_units > baseline[view.view_id].expired_units:
            reasons.append(f"{view.view_id}: expiry increases by {view.expired_units - baseline[view.view_id].expired_units} units")
        if Decimal(view.ending_stock_eur) > Decimal(baseline[view.view_id].ending_stock_eur):
            reasons.append(f"{view.view_id}: ending stock increases")
    return reasons


def optimise(position: dict[str, Any]) -> DecisionResult:
    """Select the lowest-cash safe plan after exact physical replay."""
    started = perf_counter()
    base_lines = current_plan(position)
    current = replay_plan(position, "CURRENT", base_lines)
    candidates = generate_plans(position)
    survivors: list[PlanResult] = []
    rejected: list[dict[str, Any]] = []
    replayed = preflight_rejected = 0
    for index, plan in enumerate(candidates, start=1):
        errors = validate_plan(position, plan)
        plan_id = f"PLAN-{index:02d}"
        if errors:
            preflight_rejected += 1
            rejected.append({"plan_id": plan_id, "reasons": errors, "cash_eur": None})
            continue
        result = replay_plan(position, plan_id, plan)
        replayed += 1
        reasons = _rejections(current, result)
        if reasons:
            rejected.append({"plan_id": plan_id, "reasons": reasons, "cash_eur": result.cash_eur, "lines": list(result.lines)})
        else:
            survivors.append(result)
    if not survivors:
        raise RuntimeError("Frozen search did not retain a safe plan")
    selected = min(
        survivors,
        key=lambda result: (
            Decimal(result.cash_eur),
            sum(view.expired_units for view in result.views),
            sum(Decimal(view.ending_stock_eur) for view in result.views),
            tuple((row["product_id"], row["cases"]) for row in result.lines),
        ),
    )
    current_cases = {row["product_id"]: row["cases"] for row in current.lines}
    selected_cases = {row["product_id"]: row["cases"] for row in selected.lines}
    actions = []
    for product_id in sorted(set(current_cases) | set(selected_cases)):
        before, after = current_cases.get(product_id, 0), selected_cases.get(product_id, 0)
        product_row = position["products"][product_id]
        if before == after:
            action = "keep_order" if after else "no_order"
        elif before == 0:
            action = "order_now"
        elif after == 0:
            action = "cancel"
        elif after < before:
            action = "buy_less"
        else:
            action = "buy_more"
        actions.append({"product_id": product_id, "product_name": product_row["product_name"], "action": action, "current_cases": before, "selected_cases": after})
    higher = _view_map(selected)["higher"]
    risks = []
    for day in higher.daily_ledger:
        for expired in day["expired_lots"]:
            risks.append({**expired, "date": day["date"], "product_name": position["products"][expired["product_id"]]["product_name"]})
    identity = {
        "case_id": position["case_id"], "input_hash": position["input_hash"],
        "current": asdict(current), "selected": asdict(selected), "actions": actions,
    }
    decision_hash = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    same = tuple((row["product_id"], row["cases"]) for row in current.lines) == tuple((row["product_id"], row["cases"]) for row in selected.lines)
    return DecisionResult(
        case_id=position["case_id"], input_hash=position["input_hash"], decision_hash=decision_hash,
        verdict="keep_plan" if same else "change_plan", current=current, selected=selected,
        rejected=tuple(rejected), actions=tuple(actions), at_risk_lots=tuple(risks),
        search_report={
            "maximum_candidates": MAX_CANDIDATES, "generated_candidates": len(candidates),
            "preflight_rejected": preflight_rejected, "physically_replayed": replayed,
            "survivors": len(survivors), "elapsed_ms": round((perf_counter() - started) * 1000, 3),
        },
    )
