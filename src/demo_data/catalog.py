"""Create the fictional distributor's master data."""

from __future__ import annotations

from datetime import date, timedelta
import sqlite3

from .config import DemoConfig
from .utils import stream


CATEGORIES = ("Confectionery", "Savoury Snacks", "Dry Groceries")
PRODUCT_ROOTS = (
    "Cocoa Bites", "Fruit Chews", "Hazelnut Wafers", "Mint Drops", "Caramel Squares",
    "Salted Crisps", "Herb Crackers", "Corn Bites", "Pretzel Twists", "Seeded Snacks",
    "Tomato Pasta", "Basmati Rice", "Oat Biscuits", "Granola Pouch", "Lentil Soup",
    "Dark Chocolate", "Berry Gummies", "Vanilla Wafers", "Honey Drops", "Nougat Bar",
    "Paprika Crisps", "Rye Crackers", "Rice Bites", "Sesame Twists", "Nut Mix",
    "Spelt Pasta", "Jasmine Rice", "Cocoa Biscuits", "Muesli Pouch", "Bean Soup",
)


def insert_master_data(connection: sqlite3.Connection, config: DemoConfig) -> dict:
    """Insert reproducible suppliers, products, terms, customers and limits."""
    start = date.fromisoformat(config.history_start)
    # Master data must already be known before opening lots and pipeline orders.
    known = (start - timedelta(days=400)).isoformat()
    supplier_rng = stream(config.seed, "suppliers")
    product_rng = stream(config.seed, "products")
    customer_rng = stream(config.seed, "customers")
    suppliers = []
    minimum_values = (0, 10_000, 25_000, 10_000)
    for index in range(config.supplier_count):
        supplier_id = f"SUP-{index + 1:02d}"
        row = {
            "supplier_id": supplier_id,
            "name": f"Fictional Supplier {chr(65 + index)}",
            "order_weekday": index % 5,
            "minimum_order_value_cents": minimum_values[index],
            "delivery_charge_cents": supplier_rng.choice((0, 1_500, 3_000)),
            "standard_lead_workdays": supplier_rng.randint(2, 7),
        }
        suppliers.append(row)
        connection.execute(
            "INSERT INTO suppliers VALUES (?,?,?,?,?,?,?,?)",
            (*row.values(), known, known),
        )

    products = []
    cases = (6, 12, 24)
    shelf_lives = (90, 120, 180, 270, 365)
    for index in range(config.product_count):
        product_id = f"PRD-{index + 1:03d}"
        demand_class = ("fast", "moderate", "intermittent")[index // 10]
        category = CATEGORIES[(index % 15) // 5]
        case_size = product_rng.choice(cases)
        product = {
            "product_id": product_id,
            "name": PRODUCT_ROOTS[index],
            "category": category,
            "demand_class": demand_class,
            "base_unit": "each",
            "case_size_units": case_size,
            "storage_ml_per_unit": product_rng.randrange(150, 1001, 50),
            "normal_shelf_life_days": product_rng.choice(shelf_lives),
            "supplier_id": suppliers[index % config.supplier_count]["supplier_id"],
            "purchase_cost_cents": product_rng.randint(50, 800),
            "minimum_order_units": case_size * product_rng.randint(1, 4),
        }
        products.append(product)
        connection.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)",
            tuple(product[key] for key in (
                "product_id", "name", "category", "base_unit",
                "case_size_units", "storage_ml_per_unit", "normal_shelf_life_days",
            )) + (known, known),
        )
        connection.execute(
            "INSERT INTO supplier_product_terms VALUES (?,?,?,?,?,?,?,?,?)",
            (
                f"TERM-{index + 1:03d}", product["supplier_id"], product_id,
                product["purchase_cost_cents"], product["minimum_order_units"],
                known, None, known, known,
            ),
        )

    customers = []
    freshness = (14, 30, 60)
    lateness = (0, 2, 5)
    for index in range(config.customer_count):
        customer = {
            "customer_id": f"CUS-{index + 1:03d}",
            "name": f"Fictional Business Customer {index + 1:02d}",
            "size_class": ("small", "medium", "large")[min(index // 7, 2)],
            "accepts_partial": int(customer_rng.random() < 0.65),
            "maximum_late_workdays": customer_rng.choice(lateness),
            "minimum_remaining_shelf_life_days": customer_rng.choice(freshness),
        }
        customers.append(customer)
        connection.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)",
            (*customer.values(), known, known),
        )

    budget = config.effective_budget_cents
    connection.execute(
        "INSERT INTO planning_limits VALUES (?,?,?,?,?,?,?)",
        ("LIMIT-001", known, None, budget, config.warehouse_capacity_millilitres, known, known),
    )

    announced_start = config.future_start + timedelta(days=7)
    announced_end = announced_start + timedelta(days=9)
    if config.scenario_family == "demand_changes":
        connection.execute(
            "INSERT INTO promotions VALUES (?,?,?,?,?,?,?,?)",
            (
                "PROMO-ANNOUNCED", products[2]["product_id"], config.history_end.isoformat(),
                announced_start.isoformat(), announced_end.isoformat(), 1,
                announced_start.isoformat(), config.history_end.isoformat(),
            ),
        )
    return {"suppliers": suppliers, "products": products, "customers": customers}
