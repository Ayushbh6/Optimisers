"""SQLite schemas for operational and evaluator-only scenario records."""

from __future__ import annotations

import sqlite3
from pathlib import Path


OPERATIONAL_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE dataset_manifest (
  key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE suppliers (
  supplier_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  order_weekday INTEGER NOT NULL CHECK(order_weekday BETWEEN 0 AND 4),
  minimum_order_value_cents INTEGER NOT NULL CHECK(minimum_order_value_cents >= 0),
  delivery_charge_cents INTEGER NOT NULL CHECK(delivery_charge_cents >= 0),
  standard_lead_workdays INTEGER NOT NULL CHECK(standard_lead_workdays BETWEEN 2 AND 7),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE products (
  product_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL,
  base_unit TEXT NOT NULL CHECK(base_unit = 'each'),
  case_size_units INTEGER NOT NULL CHECK(case_size_units IN (6,12,24)),
  storage_ml_per_unit INTEGER NOT NULL CHECK(storage_ml_per_unit > 0),
  normal_shelf_life_days INTEGER NOT NULL CHECK(normal_shelf_life_days BETWEEN 90 AND 365),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE supplier_product_terms (
  term_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers,
  product_id TEXT NOT NULL REFERENCES products,
  purchase_cost_cents INTEGER NOT NULL CHECK(purchase_cost_cents BETWEEN 50 AND 800),
  minimum_order_units INTEGER NOT NULL CHECK(minimum_order_units > 0),
  effective_from TEXT NOT NULL, effective_to TEXT,
  event_date TEXT NOT NULL, known_at TEXT NOT NULL,
  UNIQUE(supplier_id, product_id, effective_from)
);
CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  size_class TEXT NOT NULL CHECK(size_class IN ('small','medium','large')),
  accepts_partial INTEGER NOT NULL CHECK(accepts_partial IN (0,1)),
  maximum_late_workdays INTEGER NOT NULL CHECK(maximum_late_workdays IN (0,2,5)),
  minimum_remaining_shelf_life_days INTEGER NOT NULL CHECK(minimum_remaining_shelf_life_days IN (14,30,60)),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE planning_limits (
  limit_id TEXT PRIMARY KEY, effective_from TEXT NOT NULL, effective_to TEXT,
  weekly_new_order_budget_cents INTEGER NOT NULL CHECK(weekly_new_order_budget_cents > 0),
  warehouse_capacity_ml INTEGER NOT NULL CHECK(warehouse_capacity_ml > 0),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE promotions (
  promotion_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products,
  announcement_date TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  planner_visible INTEGER NOT NULL CHECK(planner_visible IN (0,1)),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE customer_orders (
  customer_order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers,
  created_date TEXT NOT NULL, due_date TEXT NOT NULL,
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE customer_order_lines (
  customer_order_line_id TEXT PRIMARY KEY, customer_order_id TEXT NOT NULL REFERENCES customer_orders,
  product_id TEXT NOT NULL REFERENCES products, requested_units INTEGER NOT NULL CHECK(requested_units > 0),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL,
  UNIQUE(customer_order_id, product_id)
);
CREATE TABLE supplier_orders (
  supplier_order_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers,
  placed_date TEXT NOT NULL, expected_delivery_date TEXT NOT NULL,
  delivery_charge_cents INTEGER NOT NULL CHECK(delivery_charge_cents >= 0),
  status TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE supplier_order_lines (
  supplier_order_line_id TEXT PRIMARY KEY, supplier_order_id TEXT NOT NULL REFERENCES supplier_orders,
  product_id TEXT NOT NULL REFERENCES products,
  ordered_units INTEGER NOT NULL CHECK(ordered_units > 0),
  unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents > 0),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL,
  UNIQUE(supplier_order_id, product_id)
);
CREATE TABLE supplier_updates (
  supplier_update_id TEXT PRIMARY KEY, supplier_order_id TEXT NOT NULL REFERENCES supplier_orders,
  update_type TEXT NOT NULL CHECK(update_type IN ('delay','partial_delivery','cancellation','capacity_rejection')),
  revised_expected_date TEXT, affected_units INTEGER CHECK(affected_units IS NULL OR affected_units >= 0),
  note TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE receipts (
  receipt_id TEXT PRIMARY KEY, supplier_order_line_id TEXT NOT NULL REFERENCES supplier_order_lines,
  received_date TEXT NOT NULL, received_units INTEGER NOT NULL CHECK(received_units > 0),
  undelivered_units INTEGER NOT NULL DEFAULT 0 CHECK(undelivered_units >= 0),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE stock_lots (
  lot_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products,
  receipt_id TEXT REFERENCES receipts, received_date TEXT NOT NULL, expiry_date TEXT NOT NULL,
  acquisition_cost_cents INTEGER NOT NULL CHECK(acquisition_cost_cents > 0),
  opening_units INTEGER NOT NULL CHECK(opening_units >= 0),
  event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE shipments (
  shipment_id TEXT PRIMARY KEY, customer_order_line_id TEXT NOT NULL REFERENCES customer_order_lines,
  lot_id TEXT NOT NULL REFERENCES stock_lots, shipped_units INTEGER NOT NULL CHECK(shipped_units > 0),
  dispatch_date TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE cancellations (
  cancellation_id TEXT PRIMARY KEY, customer_order_line_id TEXT NOT NULL REFERENCES customer_order_lines,
  cancelled_units INTEGER NOT NULL CHECK(cancelled_units > 0), reason TEXT NOT NULL,
  cancellation_date TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE stock_movements (
  movement_id TEXT PRIMARY KEY, lot_id TEXT NOT NULL REFERENCES stock_lots,
  movement_type TEXT NOT NULL CHECK(movement_type IN ('opening','receipt','shipment','expiry')),
  quantity_delta_units INTEGER NOT NULL CHECK(quantity_delta_units != 0),
  source_id TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE closing_stock (
  lot_id TEXT PRIMARY KEY REFERENCES stock_lots, closing_units INTEGER NOT NULL CHECK(closing_units >= 0),
  as_of_date TEXT NOT NULL
);
CREATE INDEX ix_orders_known ON customer_orders(known_at);
CREATE INDEX ix_supplier_orders_known ON supplier_orders(known_at);
CREATE INDEX ix_movements_known ON stock_movements(known_at);
"""


EVALUATOR_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE evaluator_manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE future_customer_orders (
  customer_order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
  created_date TEXT NOT NULL, due_date TEXT NOT NULL, event_date TEXT NOT NULL
);
CREATE TABLE future_customer_order_lines (
  customer_order_line_id TEXT PRIMARY KEY,
  customer_order_id TEXT NOT NULL REFERENCES future_customer_orders,
  product_id TEXT NOT NULL, requested_units INTEGER NOT NULL CHECK(requested_units > 0),
  event_date TEXT NOT NULL, UNIQUE(customer_order_id, product_id)
);
CREATE TABLE future_supplier_conditions (
  condition_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL,
  start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  delay_workdays INTEGER NOT NULL CHECK(delay_workdays >= 0),
  fill_rate_basis_points INTEGER NOT NULL CHECK(fill_rate_basis_points BETWEEN 1 AND 10000),
  event_date TEXT NOT NULL
);
CREATE TABLE continuation_deliveries (
  delivery_id INTEGER PRIMARY KEY,
  supplier_order_line_id TEXT NOT NULL, product_id TEXT NOT NULL,
  supplier_order_id TEXT NOT NULL, arrival_date TEXT NOT NULL,
  quantity_units INTEGER NOT NULL CHECK(quantity_units > 0), expiry_date TEXT NOT NULL
);
CREATE TABLE continuation_notices (
  supplier_update_id TEXT PRIMARY KEY, supplier_order_id TEXT NOT NULL,
  update_type TEXT NOT NULL, revised_expected_date TEXT, affected_units INTEGER,
  note TEXT NOT NULL, event_date TEXT NOT NULL, known_at TEXT NOT NULL
);
"""


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """Open a database with relational checks enabled."""
    if readonly:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database(path: Path, schema: str) -> sqlite3.Connection:
    """Create a new database and refuse accidental replacement."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(path)
    # SQLite STRICT tables reject non-integral quantities and enforce non-null IDs.
    connection.executescript(schema.replace("\n);", "\n) STRICT;"))
    return connection
