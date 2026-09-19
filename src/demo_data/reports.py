"""Plain-language reports for reviewing a generated scenario."""

from __future__ import annotations

import json
from pathlib import Path

from .config import ASSUMPTIONS, DemoConfig
from .schema import connect


def write_assumptions(path: Path) -> None:
    """Write the declared assumption register."""
    rows = [
        {"name": name, "value_or_range": value, "basis": basis, "decision_effect": effect}
        for name, value, basis, effect in ASSUMPTIONS
    ]
    path.write_text(json.dumps({"label": "illustrative assumptions, not client facts", "assumptions": rows}, indent=2) + "\n")


def write_coverage(report: dict, config: DemoConfig, path: Path) -> None:
    """Write a concise scenario coverage report."""
    values = report["coverage"]
    lines = [
        "# Synthetic distributor scenario coverage",
        "",
        f"> {config.synthetic_label}",
        "",
        f"- Scenario family: `{config.scenario_family}`",
        f"- History: {config.history_start} to {config.history_end.isoformat()} (26 weeks)",
        f"- Reserved future: {config.future_start.isoformat()} to {config.future_end.isoformat()} (8 weeks)",
        f"- Historical requested units: {values['historical_requested_units']:,}",
        f"- Historical shipped units: {values['historical_shipped_units']:,}",
        f"- Historical fulfilment: {values['historical_fulfilment_percent']}%",
        f"- Units shipped by their due date: {values['on_time_shipped_units']:,}",
        f"- Cancelled units: {values['historical_cancelled_units']:,}",
        f"- Still-open customer units: {values['historical_open_customer_units']:,}",
        f"- Expired units: {values['expiry_writeoff_units']:,}",
        f"- Closing stock units: {values['closing_stock_units']:,}",
        f"- Closing stock at purchase cost: €{values['closing_stock_value_cents']/100:,.2f}",
        f"- Closing units expiring within 30 days: {values['near_expiry_closing_units_30_days']:,}",
        f"- Expiry write-off at purchase cost: €{values['expiry_writeoff_cents']/100:,.2f}",
        f"- Outstanding supplier units: {values['supplier_outstanding_units']:,}",
        f"- Outstanding stock commitments, excluding delivery charges: €{values['supplier_outstanding_value_cents']/100:,.2f}",
        f"- Future customer requests held by evaluator: {values.get('future_customer_orders', 0):,} orders / {values.get('future_customer_order_units', 0):,} units",
        "",
        "These figures describe a constructed scenario. They are not observed client performance or achieved savings.",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_walkthrough(operational_path: Path, config: DemoConfig, path: Path) -> None:
    """Trace one customer line and one supplier line through linked records."""
    db = connect(operational_path)
    customer = db.execute(
        """
        SELECT co.customer_order_id, col.customer_order_line_id, c.name customer, p.name product,
               co.created_date, co.due_date, col.requested_units,
               COALESCE((SELECT SUM(s.shipped_units) FROM shipments s WHERE s.customer_order_line_id=col.customer_order_line_id),0) shipped_units,
               COALESCE((SELECT SUM(ca.cancelled_units) FROM cancellations ca WHERE ca.customer_order_line_id=col.customer_order_line_id),0) cancelled_units
        FROM customer_order_lines col JOIN customer_orders co USING(customer_order_id)
        JOIN customers c USING(customer_id) JOIN products p USING(product_id)
        ORDER BY co.created_date, col.customer_order_line_id LIMIT 1
        """
    ).fetchone()
    supplier = db.execute(
        """
        SELECT so.supplier_order_id, sol.supplier_order_line_id, s.name supplier, p.name product,
               so.placed_date, so.expected_delivery_date, sol.ordered_units,
               COALESCE(SUM(r.received_units),0) received_units
        FROM supplier_order_lines sol JOIN supplier_orders so USING(supplier_order_id)
        JOIN suppliers s USING(supplier_id) JOIN products p USING(product_id)
        LEFT JOIN receipts r USING(supplier_order_line_id)
        GROUP BY sol.supplier_order_line_id ORDER BY so.placed_date, sol.supplier_order_line_id LIMIT 1
        """
    ).fetchone()
    db.close()
    lines = ["# Linked-record walkthrough", "", f"> {config.synthetic_label}", ""]
    if customer:
        lines.extend(
            [
                "## Customer order example", "",
                f"{customer['customer']} requested {customer['requested_units']} units of {customer['product']} on {customer['created_date']}, due {customer['due_date']}.",
                f"The linked records show {customer['shipped_units']} shipped, {customer['cancelled_units']} cancelled and {customer['requested_units'] - customer['shipped_units'] - customer['cancelled_units']} still open at the history boundary.",
                f"Trace keys: `{customer['customer_order_id']}` → `{customer['customer_order_line_id']}` → linked shipments/cancellation.", "",
            ]
        )
    if supplier:
        lines.extend(
            [
                "## Supplier order example", "",
                f"The business ordered {supplier['ordered_units']} units of {supplier['product']} from {supplier['supplier']} on {supplier['placed_date']}; the original expected date was {supplier['expected_delivery_date']}.",
                f"Linked receipt records contain {supplier['received_units']} units; any remainder stays visible as outstanding.",
                f"Trace keys: `{supplier['supplier_order_id']}` → `{supplier['supplier_order_line_id']}` → linked receipts, lots and stock movements.", "",
            ]
        )
    lines.append("This walkthrough proves record linkage only. It does not prove commercial savings.")
    path.write_text("\n".join(lines) + "\n")
