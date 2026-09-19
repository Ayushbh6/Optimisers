"""Independent source-to-ledger and chronological checks, including negative cases."""

from collections import Counter, defaultdict
from datetime import date, timedelta

from .utils import add_workdays


def detailed_checks(db) -> list[dict]:
    """Verify the business records against an independent reconstruction."""
    def rows(table):
        return [dict(r) for r in db.execute(f"SELECT * FROM {table}")]

    result = []

    def check(name, failures):
        result.append(dict(check=name, passed=not failures, failure_count=len(failures), examples=failures[:5], details={}))

    products = {r["product_id"]: r for r in rows("products")}
    lots = {r["lot_id"]: r for r in rows("stock_lots")}
    customers = {r["customer_id"]: r for r in rows("customers")}
    orders = {r["customer_order_id"]: r for r in rows("customer_orders")}
    lines = {r["customer_order_line_id"]: r for r in rows("customer_order_lines")}
    po = {r["supplier_order_id"]: r for r in rows("supplier_orders")}
    plines = {r["supplier_order_line_id"]: r for r in rows("supplier_order_lines")}
    receipts = {r["receipt_id"]: r for r in rows("receipts")}
    shipments = {r["shipment_id"]: r for r in rows("shipments")}
    cancels = rows("cancellations")
    movements = rows("stock_movements")
    end = dict(db.execute("SELECT key,value FROM dataset_manifest"))["history_end"]
    fail = []
    for table in ("supplier_updates", "receipts", "customer_orders", "supplier_orders", "shipments", "cancellations", "stock_movements"):
        fail.extend(dict(table=table, id=r[next(iter(r))]) for r in rows(table) if r["known_at"] > end)
    check("no_unreleased_future_operational_events", fail)

    # Expected physical movements come from their source tables, not the ledger.
    expected = Counter()
    invalid = []
    for lot in lots.values():
        if lot["opening_units"]:
            expected[(lot["lot_id"], "opening", lot["opening_units"], lot["lot_id"], lot["event_date"])] += 1
        if lot["receipt_id"]:
            r = receipts[lot["receipt_id"]]
            line = plines[r["supplier_order_line_id"]]
            if lot["product_id"] != line["product_id"] or lot["acquisition_cost_cents"] != line["unit_cost_cents"]:
                invalid.append(lot["lot_id"])
            if lot["opening_units"] or lot["received_date"] != r["received_date"]:
                invalid.append(lot["lot_id"])
            expected[(lot["lot_id"], "receipt", r["received_units"], r["receipt_id"], r["received_date"])] += 1
    receipt_lots = Counter(lot["receipt_id"] for lot in lots.values() if lot["receipt_id"])
    invalid.extend(key for key in receipts if receipt_lots[key] != 1)
    for s in shipments.values():
        expected[(s["lot_id"], "shipment", -s["shipped_units"], s["shipment_id"], s["dispatch_date"])] += 1
        if lots[s["lot_id"]]["product_id"] != lines[s["customer_order_line_id"]]["product_id"]:
            invalid.append(s["shipment_id"])
    actual = Counter((m["lot_id"], m["movement_type"], m["quantity_delta_units"], m["source_id"], m["event_date"])
                     for m in movements if m["movement_type"] != "expiry")
    invalid.extend(str(item) for item in (expected-actual) + (actual-expected))
    check("source_records_match_physical_movements", invalid)

    balance = defaultdict(int)
    failures = []
    phases = {"opening": 0, "expiry": 1, "receipt": 2, "shipment": 5}
    for m in sorted(movements, key=lambda x: (x["event_date"], phases[x["movement_type"]], x["movement_id"])):
        lot = lots[m["lot_id"]]
        day = date.fromisoformat(m["event_date"])
        if m["movement_type"] == "expiry":
            if m["quantity_delta_units"] != -balance[m["lot_id"]] or m["event_date"] != lot["expiry_date"]:
                failures.append(m["movement_id"])
        if m["movement_type"] == "shipment":
            s = shipments.get(m["source_id"])
            if s:
                line = lines[s["customer_order_line_id"]]
                order = orders[line["customer_order_id"]]
                customer = customers[order["customer_id"]]
                threshold = (day + timedelta(days=customer["minimum_remaining_shelf_life_days"])).isoformat()
                eligible = [key for key, qty in balance.items() if qty > 0
                            and lots[key]["product_id"] == line["product_id"]
                            and lots[key]["expiry_date"] >= threshold]
                eligible.sort(key=lambda key: (lots[key]["expiry_date"], lots[key]["received_date"], key))
                if not eligible or eligible[0] != m["lot_id"] or m["event_date"] < order["due_date"]:
                    failures.append(m["movement_id"])
        balance[m["lot_id"]] += m["quantity_delta_units"]
        if balance[m["lot_id"]] < 0:
            failures.append(m["movement_id"])
        if m["movement_type"] in ("shipment", "receipt") and day.weekday() >= 5:
            failures.append(m["movement_id"])
    closing = {r["lot_id"]: r for r in rows("closing_stock")}
    for key, lot in lots.items():
        if key not in closing or closing[key]["closing_units"] != balance[key] or closing[key]["as_of_date"] != end:
            failures.append(key)
        if lot["expiry_date"] <= end and balance[key] > 0:
            failures.append(key)
    check("independent_fefo_expiry_and_complete_closing_ledger", failures)

    fulfilled, cancelled = defaultdict(int), defaultdict(int)
    dispatch_days = defaultdict(set)
    failures = []
    for s in shipments.values():
        fulfilled[s["customer_order_line_id"]] += s["shipped_units"]
        dispatch_days[s["customer_order_line_id"]].add(s["dispatch_date"])
    for c in cancels:
        key = c["customer_order_line_id"]
        order = orders[lines[key]["customer_order_id"]]
        customer = customers[order["customer_id"]]
        deadline = add_workdays(date.fromisoformat(order["due_date"]), customer["maximum_late_workdays"]).isoformat()
        if c["cancellation_date"] != deadline:
            failures.append(c["cancellation_id"])
        cancelled[key] += c["cancelled_units"]
    for key, line in lines.items():
        order = orders[line["customer_order_id"]]
        customer = customers[order["customer_id"]]
        deadline = add_workdays(date.fromisoformat(order["due_date"]), customer["maximum_late_workdays"]).isoformat()
        remainder = line["requested_units"] - fulfilled[key] - cancelled[key]
        if remainder < 0 or (deadline <= end and remainder != 0):
            failures.append(key)
        if not customer["accepts_partial"] and len(dispatch_days[key]) > 1:
            failures.append(key)
    check("customer_windows_close_and_whole_lines_dispatch_together", failures)

    failures = []
    suppliers = {r["supplier_id"]: r for r in rows("suppliers")}
    for order in po.values():
        if date.fromisoformat(order["placed_date"]).weekday() != suppliers[order["supplier_id"]]["order_weekday"]:
            failures.append(order["supplier_order_id"])
        if order["status"] != "open":
            failures.append(order["supplier_order_id"])
    for r in receipts.values():
        if r["received_date"] < po[plines[r["supplier_order_line_id"]]["supplier_order_id"]]["placed_date"]:
            failures.append(r["receipt_id"])
    check("supplier_order_calendar_and_immutable_status", failures)
    return result


def continuation_check(db, evaluator) -> dict:
    """Every outstanding historic order must have an evaluator continuation."""
    pending = defaultdict(int)
    failures = []
    end = dict(db.execute("SELECT key,value FROM dataset_manifest"))["history_end"]
    for r in evaluator.execute("SELECT * FROM continuation_deliveries"):
        pending[r["supplier_order_line_id"]] += r["quantity_units"]
        if r["arrival_date"] <= end:
            failures.append(r["supplier_order_line_id"])
    for line in db.execute("SELECT * FROM supplier_order_lines"):
        received = db.execute("SELECT COALESCE(SUM(received_units),0) FROM receipts WHERE supplier_order_line_id=?",
                              (line["supplier_order_line_id"],)).fetchone()[0]
        if pending.pop(line["supplier_order_line_id"], 0) != line["ordered_units"] - received:
            failures.append(line["supplier_order_line_id"])
    failures.extend(pending)
    for table in ("future_customer_orders", "future_customer_order_lines", "future_supplier_conditions", "continuation_notices"):
        if evaluator.execute(f"SELECT COUNT(*) FROM {table} WHERE event_date <= ?", (end,)).fetchone()[0]:
            failures.append(table)
    # Cross-file identifiers must also resolve; SQLite FK checks cannot do this.
    for table, field, target in (("future_customer_orders", "customer_id", "customers"),
                                ("future_customer_order_lines", "product_id", "products"),
                                ("future_supplier_conditions", "supplier_id", "suppliers")):
        valid = {r[0] for r in db.execute(f"SELECT {field} FROM {target}")}
        failures.extend(r[0] for r in evaluator.execute(f"SELECT DISTINCT {field} FROM {table}") if r[0] not in valid)
    return dict(check="evaluator_references_and_open_orders_continue", passed=not failures,
                failure_count=len(failures), examples=failures[:5], details={})
