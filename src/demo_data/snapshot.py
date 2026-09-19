"""As-of interfaces that cannot expose evaluator-only future events."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from .schema import connect
from .storage import validate_output


EXPORTED_TABLES = (
    "suppliers", "products", "supplier_product_terms", "customers", "planning_limits",
    "promotions", "customer_orders", "customer_order_lines", "supplier_orders",
    "supplier_order_lines", "supplier_updates", "receipts", "stock_lots", "shipments",
    "cancellations", "stock_movements",
)


def snapshot(operational_path: Path, as_of: str | date, *, phase: str = "end_of_day") -> dict[str, list[dict]]:
    """Return knowledge at day end or just before the day's ordering decision."""
    if phase not in {"end_of_day", "before_ordering"}:
        raise ValueError("phase must be end_of_day or before_ordering")
    cutoff = as_of.isoformat() if isinstance(as_of, date) else date.fromisoformat(as_of).isoformat()
    db = connect(operational_path, readonly=True)
    manifest = dict(db.execute("SELECT key, value FROM dataset_manifest"))
    if not manifest["history_start"] <= cutoff <= manifest["history_end"]:
        db.close()
        raise ValueError("Snapshot date must be within the generated historical interval")
    result = {}
    for table in EXPORTED_TABLES:
        rows = db.execute(f"SELECT * FROM {table} WHERE known_at <= ? ORDER BY rowid", (cutoff,)).fetchall()
        result[table] = [dict(row) for row in rows]
    if phase == "before_ordering":
        for table in ("supplier_orders", "supplier_order_lines", "shipments", "cancellations"):
            result[table] = [r for r in result[table] if r["known_at"] < cutoff]
        result["stock_movements"] = [r for r in result["stock_movements"]
                                     if r["known_at"] < cutoff or r["movement_type"] != "shipment"]
    # Generation classes and exact demand multipliers belong to the evaluator,
    # not the information a distributor knows about its future customers.
    for product in result["products"]:
        product.pop("demand_class", None)
    result["promotions"] = [row for row in result["promotions"] if row["planner_visible"]]
    for promotion in result["promotions"]:
        promotion.pop("demand_multiplier_basis_points", None)
    received = defaultdict(int)
    for row in result["receipts"]:
        received[row["supplier_order_line_id"]] += row["received_units"]
    order_totals = defaultdict(lambda: [0, 0])
    for line in result["supplier_order_lines"]:
        line["received_units"] = received[line["supplier_order_line_id"]]
        line["outstanding_units"] = line["ordered_units"] - line["received_units"]
        totals = order_totals[line["supplier_order_id"]]
        totals[0] += line["ordered_units"]
        totals[1] += line["received_units"]
    for order in result["supplier_orders"]:
        ordered, arrived = order_totals[order["supplier_order_id"]]
        order["status"] = "received" if arrived == ordered else "partially_received" if arrived else "open"
    shipped, cancelled = defaultdict(int), defaultdict(int)
    for row in result["shipments"]:
        shipped[row["customer_order_line_id"]] += row["shipped_units"]
    for row in result["cancellations"]:
        cancelled[row["customer_order_line_id"]] += row["cancelled_units"]
    for line in result["customer_order_lines"]:
        key = line["customer_order_line_id"]
        line.update(shipped_units=shipped[key], cancelled_units=cancelled[key],
                    outstanding_units=line["requested_units"]-shipped[key]-cancelled[key])
    movements = result["stock_movements"]
    balances: dict[str, int] = {}
    for movement in movements:
        balances[movement["lot_id"]] = balances.get(movement["lot_id"], 0) + movement["quantity_delta_units"]
    result["snapshot_stock"] = [
        {"lot_id": lot_id, "as_of_date": cutoff, "quantity_units": units}
        for lot_id, units in sorted(balances.items()) if units
    ]
    result["snapshot_manifest"] = [
        {
            "synthetic_label": manifest["synthetic_label"],
            "schema_version": manifest["schema_version"],
            "as_of_date": cutoff,
            "cutoff_phase": phase,
        }
    ]
    db.close()
    return result


def export_csv(operational_path: Path, output_dir: Path, as_of: str | date, *, phase: str = "end_of_day") -> list[Path]:
    """Export one restricted operational snapshot and refuse replacement."""
    data = snapshot(operational_path, as_of, phase=phase)
    output_dir = validate_output(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite snapshot directory: {output_dir}")
    output_dir.mkdir(parents=True)
    written = []
    db = connect(operational_path, readonly=True)
    for table, rows in data.items():
        path = output_dir / f"{table}.csv"
        with path.open("w", newline="") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            else:
                columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
                if table == "promotions":
                    columns = [x for x in columns if x != "demand_multiplier_basis_points"]
                if table == "snapshot_stock":
                    columns = ["lot_id", "as_of_date", "quantity_units"]
                csv.writer(handle).writerow(columns)
        written.append(path)
    db.close()
    return written
