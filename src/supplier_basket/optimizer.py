"""Bounded whole-case search judged only by exact physical replay."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from math import ceil
from time import perf_counter
from typing import Any

from .contracts import CandidateResult, DecisionResult, ReplayResult
from .reconciliation import load_contract
from .replay import buyer_basket, replay, validate_basket


MAX_ALTERNATIVES = 12


def _signature(basket: list[dict[str, int]]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((row["product_id"], row["cases"]) for row in basket if row["cases"] > 0))


def _basket(signature: tuple[tuple[str, int], ...]) -> list[dict[str, int]]:
    return [{"product_id": product_id, "cases": cases} for product_id, cases in signature]


def _merchandise(signature: tuple[tuple[str, int], ...], products: dict[str, dict[str, Any]]) -> Decimal:
    return sum(
        Decimal(products[product_id]["unit_cost_eur"]) * products[product_id]["case_size"] * cases
        for product_id, cases in signature
    )


def _candidate_id(prefix: str, action: str, product_id: str, repair_id: str | None = None) -> str:
    identifier = f"{prefix}-{action}-{product_id[-3:]}"
    return f"{identifier}-REPAIR-{repair_id[-3:]}" if repair_id else identifier


def generate_candidates(case: dict[str, Any]) -> list[tuple[str, str, list[dict[str, int]]]]:
    """Generate a deterministic, explicitly capped neighborhood around the buyer basket."""
    contract = load_contract()
    products = {row["product_id"]: row for row in contract["products"]}
    suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    case_contract = next(row for row in contract["cases"] if row["case_id"] == case["case_id"])
    minimum = Decimal(suppliers[case["supplier_id"]]["minimum_merchandise_eur"])
    eligible_repairs = case_contract["minimum_repair_product_ids"]
    prefix = {"positive_moq_composition": "POS", "unsafe_cheaper_delivery_loss": "UNS", "no_change_control": "CTL"}[case["case_id"]]
    base = {row["product_id"]: row["cases"] for row in buyer_basket(case)}
    booked_products = {row["product_id"] for row in case["booked_lines"]}
    seen: set[tuple[tuple[str, int], ...]] = {_signature(buyer_basket(case))}
    output: list[tuple[str, str, list[dict[str, int]]]] = []
    reductions: list[tuple[str, dict[str, int], bool]] = []

    def add(candidate_id: str, reason: str, quantities: dict[str, int]) -> None:
        if len(output) >= MAX_ALTERNATIVES:
            return
        signature = tuple(sorted((product_id, cases) for product_id, cases in quantities.items() if cases > 0))
        if signature in seen:
            return
        seen.add(signature)
        output.append((candidate_id, reason, _basket(signature)))

    # One-case reductions and increases are the first, most explainable edits.
    for product_id in sorted(base):
        quantities = dict(base)
        quantities[product_id] -= 1
        below_minimum = _merchandise(tuple(sorted((key, value) for key, value in quantities.items() if value > 0)), products) < minimum
        reductions.append((product_id, quantities, below_minimum))
        # A one-case line with no booked demand is an oversized top-up. When
        # removing it breaches MOQ, only its valid repaired baskets are useful;
        # the unrepaired zero-line state is a duplicate dead end.
        if not (base[product_id] == 1 and product_id not in booked_products and below_minimum):
            add(_candidate_id(prefix, "RED", product_id) + "-1", f"Reduce {product_id} by one whole case", quantities)
    for product_id in sorted(base):
        quantities = dict(base)
        quantities[product_id] += 1
        add(_candidate_id(prefix, "INC", product_id) + "-1", f"Increase {product_id} by one whole case", quantities)

    # Repair an under-minimum reduction with the smallest whole-case top-up of
    # one other product already needed in this case.
    for reduced_id, reduced, below_minimum in reductions:
        if not below_minimum:
            continue
        for repair_id in eligible_repairs:
            if repair_id == reduced_id or repair_id not in base:
                continue
            quantities = dict(reduced)
            case_value = Decimal(products[repair_id]["unit_cost_eur"]) * products[repair_id]["case_size"]
            missing = minimum - _merchandise(tuple(sorted((key, value) for key, value in quantities.items() if value > 0)), products)
            quantities[repair_id] += ceil(missing / case_value)
            action = "RM" if base[reduced_id] == 1 else "RED"
            add(_candidate_id(prefix, action, reduced_id, repair_id), f"Reduce {reduced_id}; restore the supplier minimum with {repair_id}", quantities)

    # If the cap still has room, test complete removal of multi-case lines.
    for removed_id in sorted(base):
        if len(output) >= MAX_ALTERNATIVES or base[removed_id] == 1:
            continue
        reduced = dict(base)
        reduced[removed_id] = 0
        current = _merchandise(tuple(sorted((key, value) for key, value in reduced.items() if value > 0)), products)
        if current >= minimum:
            add(_candidate_id(prefix, "RM", removed_id), f"Remove the complete {removed_id} line", reduced)
            continue
        for repair_id in eligible_repairs:
            if repair_id == removed_id or repair_id not in base:
                continue
            quantities = dict(reduced)
            case_value = Decimal(products[repair_id]["unit_cost_eur"]) * products[repair_id]["case_size"]
            quantities[repair_id] += ceil((minimum - current) / case_value)
            add(_candidate_id(prefix, "RM", removed_id, repair_id), f"Remove {removed_id}; restore the supplier minimum with {repair_id}", quantities)
    return output


def _safe_against(baseline: ReplayResult, candidate: ReplayResult) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if candidate.accounting_errors:
        reasons.append("Physical accounting did not reconcile")
    if candidate.on_time_units < baseline.on_time_units or candidate.complete_lines < baseline.complete_lines:
        lost = baseline.on_time_units - candidate.on_time_units
        reasons.append(f"Booked delivery regression: {lost} fewer on-time units")
    if candidate.expired_units > baseline.expired_units or Decimal(candidate.expired_cost_eur) > Decimal(baseline.expired_cost_eur):
        reasons.append("Expiry is higher than the buyer basket")
    if Decimal(candidate.ending_stock_plus_commitments_eur) > Decimal(baseline.ending_stock_plus_commitments_eur):
        reasons.append("Ending stock plus commitments is higher than the buyer basket")
    return not reasons, reasons


def _selection_key(result: ReplayResult) -> tuple[Any, ...]:
    return (
        Decimal(result.average_daily_exposure_eur),
        Decimal(result.expired_cost_eur),
        Decimal(result.delivery_charge_eur),
        tuple((row["product_id"], row["cases"]) for row in result.lines),
    )


def optimise(ledger: dict[str, Any]) -> DecisionResult:
    """Replay every feasible candidate and select the safest lowest-exposure survivor."""
    started = perf_counter()
    case = ledger["case"]
    case_contract = next(row for row in load_contract()["cases"] if row["case_id"] == case["case_id"])
    baseline_basket = buyer_basket(case)
    baseline = replay(case, "BUYER", baseline_basket)
    if baseline.accounting_errors:
        raise AssertionError("Buyer basket physical replay did not reconcile")
    candidates: list[CandidateResult] = []
    survivors = [baseline]
    for candidate_id, reason, basket in generate_candidates(case):
        preflight = validate_basket(case, basket)
        if preflight:
            candidates.append(CandidateResult(candidate_id, reason, tuple(basket), tuple(preflight), None, "rejected_preflight", tuple(preflight)))
            continue
        physical = replay(case, candidate_id, basket)
        safe, rejection = _safe_against(baseline, physical)
        if safe:
            survivors.append(physical)
        candidates.append(CandidateResult(candidate_id, reason, tuple(basket), (), physical, "survivor" if safe else "rejected_physical", tuple(rejection)))
    selected = min(survivors, key=_selection_key)
    baseline_signature = tuple((row["product_id"], row["cases"]) for row in baseline.lines)
    selected_signature = tuple((row["product_id"], row["cases"]) for row in selected.lines)
    verdict = "accept_proposed" if selected_signature != baseline_signature else "retain_buyer"
    before = {row["product_id"]: row for row in baseline.lines}
    after = {row["product_id"]: row for row in selected.lines}
    changes = []
    for product_id in sorted(set(before) | set(after)):
        old_cases = before.get(product_id, {}).get("cases", 0)
        new_cases = after.get(product_id, {}).get("cases", 0)
        if old_cases == new_cases:
            continue
        changes.append({
            "product_id": product_id,
            "buyer_cases": old_cases,
            "selected_cases": new_cases,
            "change_cases": new_cases - old_cases,
            "reason": "Removed unnecessary minimum-order top-up" if new_cases == 0 else "Used an already-needed product to satisfy the supplier minimum",
        })
    lower_cash = Decimal(selected.immediate_cash_eur) - Decimal(baseline.immediate_cash_eur)
    if verdict == "accept_proposed":
        summary = f"Use the revised basket. It needs €{abs(lower_cash):.2f} less immediate cash and protects all {baseline.booked_units} booked units."
    else:
        summary = "Keep the buyer basket. No lower-exposure alternative protects every booked delivery."
        challenged = case_contract.get("challenged_basket")
        challenged_signature = _signature(challenged["lines"]) if challenged else None
        challenged_result = next(
            (row for row in candidates if row.replay and _signature(list(row.basket)) == challenged_signature),
            None,
        )
        if challenged_result:
            cash_difference = Decimal(baseline.immediate_cash_eur) - Decimal(challenged_result.replay.immediate_cash_eur)
            delivery_loss = baseline.on_time_units - challenged_result.replay.on_time_units
            summary += f" The challenged basket needs €{cash_difference:.2f} less cash but leaves {delivery_loss} booked units late."
    risks = tuple(
        f"{failure['line_id']}: {failure['undelivered_units']} {failure['product_id']} units late on {failure['due_date']}"
        for row in candidates
        if row.decision_status == "rejected_physical" and row.replay
        for failure in row.replay.delivery_failures
    )
    payload = {
        "case_id": case["case_id"],
        "input_hash": ledger["input_hash"],
        "verdict": verdict,
        "buyer": asdict(baseline),
        "selected": asdict(selected),
        "changes": changes,
    }
    decision_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    physically_replayed = sum(row.replay is not None for row in candidates)
    survivor_count = sum(row.decision_status == "survivor" for row in candidates)
    return DecisionResult(
        case_id=case["case_id"],
        input_hash=ledger["input_hash"],
        decision_hash=decision_hash,
        verdict=verdict,
        buyer=baseline,
        selected=selected,
        candidates=tuple(candidates),
        product_changes=tuple(changes),
        summary=summary,
        risks=risks,
        assumptions=(
            "Synthetic case study; not realised client savings",
            "Only records available by the 18 September 2026 09:00 decision were used",
            "Customer freshness requires at least 60 calendar days remaining",
            "Unknown future demand, margins and shortage penalties are excluded",
        ),
        search_report={
            "max_alternatives": MAX_ALTERNATIVES,
            "max_changed_lines": load_contract()["rules"]["candidate_max_changed_lines"],
            "case_step": load_contract()["rules"]["candidate_case_step"],
            "generated_alternatives": len(candidates),
            "rejected_preflight": len(candidates) - physically_replayed,
            "physically_replayed": physically_replayed,
            "safe_alternative_survivors": survivor_count,
            "buyer_basket_always_included": True,
            "elapsed_ms": round((perf_counter() - started) * 1000, 3),
        },
    )
