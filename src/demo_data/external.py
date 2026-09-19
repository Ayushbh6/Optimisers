"""Generate customer requests and supplier conditions independent of policies."""

from __future__ import annotations

from datetime import date, timedelta
import sqlite3

from .config import DemoConfig, GENERATION_RULES as RULES
from .utils import add_workdays, date_range, stable_fraction, stream


ORDER_PROBABILITY = RULES["order_probability"]
SIZE_MULTIPLIER = RULES["customer_size_multiplier"]
QUANTITY_RANGE = RULES["positive_quantity_range"]


def generate_requests(
    config: DemoConfig,
    catalog: dict,
    start: date,
    end: date,
    period: str,
) -> list[dict]:
    """Generate coherent order headers with a two-stage occurrence/quantity model."""
    occurrence_rng = stream(config.seed, f"{period}-order-occurrence")
    quantity_rng = stream(config.seed, f"{period}-order-quantity")
    preference_rng = stream(config.seed, "customer-preferences")
    preferences = {
        customer["customer_id"]: set(preference_rng.sample(range(len(catalog["products"])), RULES["preferred_products_per_customer"]))
        for customer in catalog["customers"]
    }
    requests = []
    order_number = 0
    for day in date_range(start, end):
        if day.weekday() >= 5:
            continue
        weekday_factor = RULES["weekday_probability_multiplier"][day.weekday()]
        category_factor = {
            category: 0.82 + 0.36 * stable_fraction(config.seed, f"category:{category}:{day.isoformat()}")
            for category in {product["category"] for product in catalog["products"]}
        }
        for customer in catalog["customers"]:
            lines = []
            for index in sorted(preferences[customer["customer_id"]]):
                product = catalog["products"][index]
                probability = (
                    ORDER_PROBABILITY[product["demand_class"]]
                    * SIZE_MULTIPLIER[customer["size_class"]]
                    * weekday_factor
                    * category_factor[product["category"]]
                )
                multiplier = _demand_multiplier(config, product, day, period)
                if occurrence_rng.random() >= probability:
                    continue
                low, high = QUANTITY_RANGE[product["demand_class"]]
                units = max(1, round(quantity_rng.randint(low, high) * multiplier))
                lines.append({"product_id": product["product_id"], "requested_units": units})
            if lines:
                order_number += 1
                due = add_workdays(day, 1 + quantity_rng.randint(0, 2))
                order_id = f"{period[:1].upper()}-CO-{order_number:06d}"
                requests.append(
                    {
                        "customer_order_id": order_id,
                        "customer_id": customer["customer_id"],
                        "created_date": day,
                        "due_date": due,
                        "lines": lines,
                    }
                )
    return requests


def _demand_multiplier(config: DemoConfig, product: dict, day: date, period: str) -> float:
    """Return declared scenario demand effects without consulting a policy."""
    if period == "future" and config.scenario_family == "demand_changes":
        if config.future_start + timedelta(days=7) <= day <= config.future_start + timedelta(days=16):
            if product["product_id"] == "PRD-003":
                return RULES["promotion_quantity_multiplier"]
        if config.future_start + timedelta(days=28) <= day <= config.future_start + timedelta(days=37):
            if product["category"] == "Savoury Snacks":
                return RULES["unexpected_quantity_multiplier"]  # not announced
    return 1.0


def supply_condition(config: DemoConfig, supplier_id: str, expected: date) -> tuple[int, int]:
    """External supply response keyed by supplier/date, independent of policy order IDs.

    This belongs to the evaluator. A planner sees only subsequently released notices.
    Short deliveries complete two workdays after the first scheduled delivery.
    """
    if config.scenario_family == "supplier_disruption":
        if expected >= date.fromisoformat(config.history_start) + timedelta(weeks=13):
            if supplier_id == "SUP-01":
                return 3, 6500
            if supplier_id == "SUP-02":
                return 2, 8000
    draw = stable_fraction(config.seed, f"supply:{supplier_id}:{expected.isoformat()}")
    return (1, 10_000) if draw < RULES["ordinary_delay_probability"] else (0, 10_000)


def write_future_events(
    connection: sqlite3.Connection,
    config: DemoConfig,
    catalog: dict,
    requests: list[dict],
) -> None:
    """Write policy-independent future events to evaluator-only storage."""
    for request in requests:
        connection.execute(
            "INSERT INTO future_customer_orders VALUES (?,?,?,?,?)",
            (
                request["customer_order_id"], request["customer_id"],
                request["created_date"].isoformat(), request["due_date"].isoformat(),
                request["created_date"].isoformat(),
            ),
        )
        for line_index, line in enumerate(request["lines"], 1):
            connection.execute(
                "INSERT INTO future_customer_order_lines VALUES (?,?,?,?,?)",
                (
                    f"{request['customer_order_id']}-L{line_index:02d}",
                    request["customer_order_id"], line["product_id"],
                    line["requested_units"], request["created_date"].isoformat(),
                ),
            )
    # Include a 30-day supply tail for orders placed near the evaluation boundary.
    for supplier in catalog["suppliers"]:
        for day in date_range(config.future_start, config.future_end + timedelta(days=RULES["supply_tail_calendar_days"])):
            if day.weekday() >= 5:
                continue
            delay, fill = supply_condition(config, supplier["supplier_id"], day)
            connection.execute(
                "INSERT INTO future_supplier_conditions VALUES (?,?,?,?,?,?,?)",
                (
                    f"FSC-{supplier['supplier_id']}-{day}", supplier["supplier_id"],
                    day.isoformat(), day.isoformat(), delay, fill, day.isoformat(),
                ),
            )
