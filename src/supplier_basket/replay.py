"""Exact 28-day physical replay for one normalized supplier basket."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from .contracts import ReplayResult
from .reconciliation import load_contract


def _money(value: Decimal) -> str:
    decimal_value = Decimal(value)
    return f"{decimal_value.quantize(Decimal('0.01')):.2f}"


def _date_range(start: date, days: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(days)]


def validate_basket(case: dict[str, Any], basket: list[dict[str, int]]) -> list[str]:
    """Check dated terms, cases, minimum, budget and receipt capacity before replay."""
    contract = load_contract()
    products = {row["product_id"]: row for row in contract["products"]}
    suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    supplier = suppliers[case["supplier_id"]]
    errors: list[str] = []
    decision_day = datetime.fromisoformat(contract["decision_timestamp"]).date()
    if decision_day.strftime("%A").upper() != supplier["order_weekday"]:
        errors.append(f"Supplier orders must be placed on {supplier['order_weekday'].title()}")
    if not (date.fromisoformat(supplier["terms_effective_from"]) <= decision_day <= date.fromisoformat(supplier["terms_effective_to"])):
        errors.append("Supplier terms are not effective on the decision date")
    if case["buyer_basket"]["arrival_date"] != supplier["expected_arrival"]:
        errors.append(f"Expected arrival must be {supplier['expected_arrival']}")
    seen: set[str] = set()
    merchandise = Decimal("0")
    receipt_units = 0
    for line in basket:
        product_id, cases = line["product_id"], line["cases"]
        if product_id in seen:
            errors.append(f"Duplicate product line: {product_id}")
        seen.add(product_id)
        product = products.get(product_id)
        if product is None or product["supplier_id"] != case["supplier_id"]:
            errors.append(f"Product is not valid for supplier: {product_id}")
            continue
        if type(cases) is not int or cases < product["product_min_cases"]:
            errors.append(f"Whole positive cases required: {product_id}")
            continue
        units = cases * product["case_size"]
        receipt_units += units
        merchandise += Decimal(product["unit_cost_eur"]) * units
    if merchandise < Decimal(supplier["minimum_merchandise_eur"]):
        errors.append(f"Supplier merchandise minimum is €{supplier['minimum_merchandise_eur']}")
    cash = merchandise + Decimal(supplier["delivery_charge_eur"])
    if cash > Decimal(contract["rules"]["weekly_cash_allowance_eur"]):
        errors.append(f"Weekly purchasing allowance is €{contract['rules']['weekly_cash_allowance_eur']}")
    if receipt_units > contract["rules"]["warehouse_receipt_capacity_units_per_day"]:
        errors.append(f"Receipt exceeds {contract['rules']['warehouse_receipt_capacity_units_per_day']} units")
    return errors


def replay(case: dict[str, Any], basket_id: str, basket: list[dict[str, int]]) -> ReplayResult:
    """Replay receipts, FEFO dispatch, freshness and expiry from declared facts."""
    preflight = validate_basket(case, basket)
    if preflight:
        raise ValueError("; ".join(preflight))
    contract = load_contract()
    products = {row["product_id"]: row for row in contract["products"]}
    suppliers = {row["supplier_id"]: row for row in contract["suppliers"]}
    case_contract = next(row for row in contract["cases"] if row["case_id"] == case["case_id"])
    supplier = suppliers[case["supplier_id"]]
    start = date.fromisoformat(contract["window_start"])
    days = _date_range(start, contract["window_days"])
    freshness = contract["rules"]["minimum_remaining_shelf_life_days"]

    lots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case["opening_stock"]:
        lots[row["product_id"]].append({
            "lot_id": row["lot_id"],
            "quantity": row["quantity_units"],
            "expiry": date.fromisoformat(row["expiry_date"]),
        })

    incoming = [
        {
            "source": "existing",
            "product_id": row["product_id"],
            "quantity": row["quantity_units"],
            "arrival": date.fromisoformat(row["arrival_date"]),
            "expiry": date.fromisoformat(row["expiry_date"]),
        }
        for row in case["known_incoming"]
    ]
    arrival = date.fromisoformat(case["buyer_basket"]["arrival_date"])
    normalized_lines = []
    for row in sorted(basket, key=lambda value: value["product_id"]):
        product = products[row["product_id"]]
        units = row["cases"] * product["case_size"]
        value = Decimal(product["unit_cost_eur"]) * units
        normalized_lines.append({
            "product_id": row["product_id"],
            "cases": row["cases"],
            "quantity_units": units,
            "unit_cost_eur": product["unit_cost_eur"],
            "line_value_eur": _money(value),
            "expected_arrival": arrival.isoformat(),
        })
        incoming.append({
            "source": basket_id,
            "product_id": row["product_id"],
            "quantity": units,
            "arrival": arrival,
            "expiry": date.fromisoformat(product["incoming_expiry_date"]),
        })

    orders_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    all_orders: list[dict[str, Any]] = []
    for row in case["booked_lines"]:
        order = {
            **row,
            "due": date.fromisoformat(row["due_date"]),
            "remaining": row["quantity_units"],
            "shipped": 0,
        }
        orders_by_day[order["due"]].append(order)
        all_orders.append(order)

    daily: list[dict[str, Any]] = []
    expired_units = 0
    expired_cost = Decimal("0")
    accounting_errors: list[str] = []
    for day in days:
        opening = {product_id: sum(lot["quantity"] for lot in product_lots) for product_id, product_lots in lots.items()}
        received: dict[str, int] = defaultdict(int)
        shipped: dict[str, int] = defaultdict(int)
        expired: dict[str, int] = defaultdict(int)

        for product_id, product_lots in lots.items():
            for lot in product_lots:
                if lot["quantity"] and lot["expiry"] < day:
                    quantity = lot["quantity"]
                    lot["quantity"] = 0
                    expired[product_id] += quantity
                    expired_units += quantity
                    expired_cost += Decimal(products[product_id]["unit_cost_eur"]) * quantity

        for index, row in enumerate(incoming):
            if row["arrival"] == day:
                lot_id = f"{row['source']}-{row['product_id']}-{index}"
                lots[row["product_id"]].append({"lot_id": lot_id, "quantity": row["quantity"], "expiry": row["expiry"]})
                received[row["product_id"]] += row["quantity"]

        for order in sorted(orders_by_day.get(day, []), key=lambda value: value["line_id"]):
            need = order["remaining"]
            eligible = sorted(lots[order["product_id"]], key=lambda value: (value["expiry"], value["lot_id"]))
            for lot in eligible:
                if (lot["expiry"] - day).days < freshness:
                    continue
                quantity = min(need, lot["quantity"])
                lot["quantity"] -= quantity
                need -= quantity
                shipped[order["product_id"]] += quantity
                order["shipped"] += quantity
                if not need:
                    break
            order["remaining"] = need

        closing = {product_id: sum(lot["quantity"] for lot in product_lots) for product_id, product_lots in lots.items()}
        for product_id in set(opening) | set(received) | set(shipped) | set(expired) | set(closing):
            expected_close = opening.get(product_id, 0) + received.get(product_id, 0) - shipped.get(product_id, 0) - expired.get(product_id, 0)
            if expected_close != closing.get(product_id, 0):
                accounting_errors.append(f"{day}:{product_id}: expected {expected_close}, got {closing.get(product_id, 0)}")

        stock_value = sum(
            Decimal(products[product_id]["unit_cost_eur"]) * lot["quantity"]
            for product_id, product_lots in lots.items()
            for lot in product_lots
        )
        incoming_value = sum(
            Decimal(products[row["product_id"]]["unit_cost_eur"]) * row["quantity"]
            for row in incoming
            if row["arrival"] > day
        )
        late_value = sum(
            Decimal(products[order["product_id"]]["unit_cost_eur"]) * order["remaining"]
            for order in all_orders
            if order["due"] <= day
        )
        daily.append({
            "date": day.isoformat(),
            "received_units": sum(received.values()),
            "shipped_units": sum(shipped.values()),
            "expired_units": sum(expired.values()),
            "closing_stock_eur": _money(stock_value),
            "open_incoming_eur": _money(incoming_value),
            "past_due_commitments_eur": _money(late_value),
            "exposure_eur": _money(stock_value + incoming_value + late_value),
        })

    merchandise = sum(Decimal(row["line_value_eur"]) for row in normalized_lines)
    delivery = Decimal(supplier["delivery_charge_eur"])
    ending_stock = sum(
        Decimal(products[product_id]["unit_cost_eur"]) * lot["quantity"]
        for product_id, product_lots in lots.items()
        for lot in product_lots
    )
    ending_incoming = sum(
        Decimal(products[row["product_id"]]["unit_cost_eur"]) * row["quantity"]
        for row in incoming
        if row["arrival"] > days[-1]
    )
    undelivered = sum(Decimal(products[row["product_id"]]["unit_cost_eur"]) * row["remaining"] for row in all_orders)
    exposure_sum = sum(Decimal(row["exposure_eur"]) for row in daily)
    delivery_failures = tuple(
        {
            "line_id": row["line_id"],
            "customer_id": row["customer_id"],
            "product_id": row["product_id"],
            "due_date": row["due_date"],
            "requested_units": row["quantity_units"],
            "on_time_units": row["shipped"],
            "undelivered_units": row["remaining"],
        }
        for row in all_orders
        if row["remaining"]
    )
    return ReplayResult(
        basket_id=basket_id,
        lines=tuple(normalized_lines),
        merchandise_eur=_money(merchandise),
        delivery_charge_eur=_money(delivery),
        immediate_cash_eur=_money(merchandise + delivery),
        on_time_units=sum(row["shipped"] for row in all_orders),
        complete_lines=sum(1 for row in all_orders if row["remaining"] == 0),
        booked_units=sum(row["quantity_units"] for row in all_orders),
        booked_lines=len(all_orders),
        expired_units=expired_units,
        expired_cost_eur=_money(expired_cost),
        average_daily_exposure_eur=_money(exposure_sum / contract["window_days"]),
        sum_28_daily_exposure_eur=_money(exposure_sum),
        ending_stock_eur=_money(ending_stock),
        ending_incoming_eur=_money(ending_incoming),
        ending_undelivered_commitments_eur=_money(undelivered),
        ending_stock_plus_commitments_eur=_money(ending_stock + ending_incoming + undelivered),
        delivery_failures=delivery_failures,
        daily_ledger=tuple(daily),
        accounting_errors=tuple(accounting_errors),
    )


def buyer_basket(case: dict[str, Any]) -> list[dict[str, int]]:
    """Return the normalized buyer basket in the optimizer's minimal shape."""
    return [{"product_id": row["product_id"], "cases": row["cases"]} for row in case["buyer_basket"]["lines"]]
