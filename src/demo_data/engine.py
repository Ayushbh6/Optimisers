"""Chronological history engine for the fictional distributor."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import math
import sqlite3

from .config import DemoConfig, GENERATION_RULES as RULES
from .external import supply_condition
from .utils import add_workdays, date_range


class HistoryEngine:
    """Turn declared external requests into coherent historical records."""

    def __init__(self, connection: sqlite3.Connection, config: DemoConfig, catalog: dict):
        self.db = connection
        self.config = config
        self.catalog = catalog
        self.products = {row["product_id"]: row for row in catalog["products"]}
        self.suppliers = {row["supplier_id"]: row for row in catalog["suppliers"]}
        self.customers = {row["customer_id"]: row for row in catalog["customers"]}
        self.lots: dict[str, dict] = {}
        self.order_lines: dict[str, dict] = {}
        self.pending_deliveries: list[dict] = []
        self.pending_notices: list[tuple] = []
        self.requested_by_day: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.po_counter = self.receipt_counter = self.lot_counter = 0
        self.shipment_counter = self.cancellation_counter = self.movement_counter = 0
        self.week_spend = 0

    def run(self, requests: list[dict]) -> None:
        """Build all historical events in the agreed within-day sequence."""
        start = date.fromisoformat(self.config.history_start)
        self._create_opening_stock(start)
        requests_by_day: dict[date, list[dict]] = defaultdict(list)
        for request in requests:
            requests_by_day[request["created_date"]].append(request)

        for day in date_range(start, self.config.history_end):
            if day.weekday() == 0:
                self.week_spend = 0
            self._expire(day)
            if day.weekday() < 5:
                self._receive(day)
            self._record_requests(day, requests_by_day[day])
            if day.weekday() < 5:
                self._place_orders(day)
                self._dispatch(day)
            self._cancel_overdue(day)
        self._write_closing_stock(self.config.history_end)
        # PO status remains its immutable placement state. Snapshots derive status
        # from receipts known by their own cutoff, never from the completed history.

    def _create_opening_stock(self, start: date) -> None:
        for index, product in enumerate(self.catalog["products"], 1):
            daily = RULES["opening_daily_units_by_class"][product["demand_class"]]
            weeks = RULES["ample_opening_cover_weeks"] if self.config.scenario_family == "ample_stock" else RULES["opening_cover_weeks"]
            units = max(product["case_size_units"], round(daily * 7 * weeks))
            if self.config.scenario_family == "ageing_stock" and index > 20:
                units *= RULES["ageing_opening_slow_stock_multiplier"]
                remaining_days = min(product["normal_shelf_life_days"], 182 + 14 + index % 12)
            else:
                remaining_days = max(75, product["normal_shelf_life_days"] - 30 - index % 25)
            received = start - timedelta(days=product["normal_shelf_life_days"] - remaining_days)
            expiry = received + timedelta(days=product["normal_shelf_life_days"])
            lot_id = f"OPEN-{index:03d}"
            self.lots[lot_id] = {
                "lot_id": lot_id,
                "product_id": product["product_id"],
                "received_date": received,
                "expiry_date": expiry,
                "cost": product["purchase_cost_cents"],
                "remaining": units,
            }
            self.db.execute(
                "INSERT INTO stock_lots VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    lot_id, product["product_id"], None, received.isoformat(), expiry.isoformat(),
                    product["purchase_cost_cents"], units, start.isoformat(), start.isoformat(),
                ),
            )
            self._movement(lot_id, "opening", units, lot_id, start)

        # A declared incoming order makes opening pipeline stock explicit.
        supplier = self.catalog["suppliers"][0]
        products = [p for p in self.catalog["products"] if p["supplier_id"] == supplier["supplier_id"]][:2]
        placed = start - timedelta(days=7)  # previous supplier ordering Monday
        expected = add_workdays(placed, supplier["standard_lead_workdays"])
        expected = max(expected, start)
        self._create_po(supplier, [(p, p["minimum_order_units"]) for p in products], placed, expected, opening=True)

    def _record_requests(self, day: date, requests: list[dict]) -> None:
        for request in requests:
            created = request["created_date"].isoformat()
            self.db.execute(
                "INSERT INTO customer_orders VALUES (?,?,?,?,?,?)",
                (request["customer_order_id"], request["customer_id"], created, request["due_date"].isoformat(), created, created),
            )
            for line_index, source_line in enumerate(request["lines"], 1):
                line_id = f"{request['customer_order_id']}-L{line_index:02d}"
                self.db.execute(
                    "INSERT INTO customer_order_lines VALUES (?,?,?,?,?,?)",
                    (line_id, request["customer_order_id"], source_line["product_id"], source_line["requested_units"], created, created),
                )
                self.order_lines[line_id] = {
                    "line_id": line_id,
                    "customer_id": request["customer_id"],
                    "product_id": source_line["product_id"],
                    "requested": source_line["requested_units"],
                    "remaining": source_line["requested_units"],
                    "created": day,
                    "due": request["due_date"],
                }
                self.requested_by_day[day][source_line["product_id"]] += source_line["requested_units"]

    def _place_orders(self, day: date) -> None:
        for supplier in self.catalog["suppliers"]:
            if supplier["order_weekday"] != day.weekday():
                continue
            candidates = []
            for product in self.catalog["products"]:
                if product["supplier_id"] != supplier["supplier_id"]:
                    continue
                horizon_end = add_workdays(day, supplier["standard_lead_workdays"]) + timedelta(days=RULES["history_review_calendar_days"])
                if self.config.scenario_family == "ample_stock" and day >= self.config.history_end - timedelta(weeks=RULES["ample_stock_campaign_final_weeks"]):
                    horizon_end += timedelta(days=RULES["ample_stock_extra_cover_calendar_days"])
                horizon = (horizon_end - day).days + 1
                recent = sum(
                    self.requested_by_day[day - timedelta(days=offset)].get(product["product_id"], 0)
                    for offset in range(1, RULES["history_average_calendar_days"]+1)
                ) / RULES["history_average_calendar_days"]
                due_by_day = defaultdict(int)
                for line in self.order_lines.values():
                    if line["product_id"] == product["product_id"] and line["due"] <= horizon_end:
                        due_by_day[max(day, line["due"])] += line["remaining"]
                known_due = sum(due_by_day.values())
                target = math.ceil(sum(max(recent, due_by_day[d]) for d in date_range(day, horizon_end)))
                # Use lots meeting the strictest declared customer requirement at
                # receipt time. Do not count stock that cannot serve those customers.
                freshness = max(c["minimum_remaining_shelf_life_days"] for c in self.customers.values())
                available = sum(lot["remaining"] for lot in self._eligible_lots(
                    product["product_id"], add_workdays(day, supplier["standard_lead_workdays"]), freshness
                ))
                pending = self._pending_product_units(product["product_id"])
                gap = target - available - pending
                if gap <= 0:
                    continue
                case = product["case_size_units"]
                units = max(product["minimum_order_units"], math.ceil(gap / case) * case)
                coverage = available / recent if recent > 0 else float("inf")
                candidates.append((known_due > available, coverage, product["product_id"], product, units))
            candidates.sort(key=lambda item: (-int(item[0]), item[1], item[2]))
            selected = []
            proposed_value = 0
            available_budget = self._weekly_budget() - self.week_spend
            for _, _, _, product, units in candidates:
                line_value = units * product["purchase_cost_cents"]
                extra_charge = supplier["delivery_charge_cents"] if not selected else 0
                if proposed_value + line_value + extra_charge <= available_budget:
                    selected.append((product, units))
                    proposed_value += line_value + extra_charge
            merchandise = sum(product["purchase_cost_cents"] * units for product, units in selected)
            if not selected or merchandise < supplier["minimum_order_value_cents"]:
                continue
            expected = add_workdays(day, supplier["standard_lead_workdays"])
            self._create_po(supplier, selected, day, expected)
            self.week_spend += merchandise + supplier["delivery_charge_cents"]

    def _create_po(self, supplier: dict, lines: list[tuple[dict, int]], placed: date, expected: date, opening: bool = False) -> None:
        self.po_counter += 1
        po_id = f"PO-{self.po_counter:05d}"
        known = placed.isoformat()
        self.db.execute(
            "INSERT INTO supplier_orders VALUES (?,?,?,?,?,?,?,?)",
            (po_id, supplier["supplier_id"], known, expected.isoformat(), supplier["delivery_charge_cents"], "open", known, known),
        )
        delay, fill_rate = supply_condition(self.config, supplier["supplier_id"], expected)
        actual = add_workdays(expected, delay)
        if delay:
            notice = expected
            self.pending_notices.append((f"UPD-{po_id}-D", po_id, "delay", actual.isoformat(), None,
                                         "Supplier notified a delivery delay.", notice.isoformat(), notice.isoformat()))
        for line_index, (product, units) in enumerate(lines, 1):
            line_id = f"{po_id}-L{line_index:02d}"
            self.db.execute(
                "INSERT INTO supplier_order_lines VALUES (?,?,?,?,?,?,?)",
                (line_id, po_id, product["product_id"], units, product["purchase_cost_cents"], known, known),
            )
            first_units = max(1, math.floor(units * fill_rate / 10_000))
            # Remaining life is fixed before transit; delays do not rejuvenate food.
            expiry = expected + timedelta(days=product["normal_shelf_life_days"] - RULES["receipt_age_days_at_expected_arrival"])
            self.pending_deliveries.append(
                {"line_id": line_id, "product_id": product["product_id"], "date": actual, "units": first_units, "po_id": po_id, "expiry": expiry}
            )
            remainder = units - first_units
            if remainder:
                self.pending_notices.append(
                    (
                        f"UPD-{line_id}-P", po_id, "partial_delivery", add_workdays(actual, 2).isoformat(),
                        remainder, "Supplier confirmed a partial first delivery.", actual.isoformat(), actual.isoformat(),
                    ),
                )
                self.pending_deliveries.append(
                    {"line_id": line_id, "product_id": product["product_id"], "date": add_workdays(actual, 2), "units": remainder, "po_id": po_id, "expiry": expiry}
                )

    def _receive(self, day: date) -> None:
        for notice in self.pending_notices:
            if notice[-1] == day.isoformat():
                self.db.execute("INSERT INTO supplier_updates VALUES (?,?,?,?,?,?,?,?)", notice)
        self.pending_notices = [n for n in self.pending_notices if n[-1] > day.isoformat()]
        due = [delivery for delivery in self.pending_deliveries if delivery["date"] == day]
        self.pending_deliveries = [delivery for delivery in self.pending_deliveries if delivery["date"] != day]
        for delivery in due:
            product = self.products[delivery["product_id"]]
            available_ml = self.config.warehouse_capacity_millilitres - self._used_capacity_ml()
            accepted = min(delivery["units"], max(0, available_ml // product["storage_ml_per_unit"]))
            undelivered = delivery["units"] - accepted
            if accepted:
                self.receipt_counter += 1
                self.lot_counter += 1
                receipt_id = f"REC-{self.receipt_counter:06d}"
                lot_id = f"LOT-{self.lot_counter:06d}"
                self.db.execute(
                    "INSERT INTO receipts VALUES (?,?,?,?,?,?,?)",
                    (receipt_id, delivery["line_id"], day.isoformat(), accepted, undelivered, day.isoformat(), day.isoformat()),
                )
                expiry = delivery["expiry"]
                self.db.execute(
                    "INSERT INTO stock_lots VALUES (?,?,?,?,?,?,?,?,?)",
                    (lot_id, product["product_id"], receipt_id, day.isoformat(), expiry.isoformat(), product["purchase_cost_cents"], 0, day.isoformat(), day.isoformat()),
                )
                self.lots[lot_id] = {
                    "lot_id": lot_id, "product_id": product["product_id"], "received_date": day,
                    "expiry_date": expiry, "cost": product["purchase_cost_cents"], "remaining": accepted,
                }
                self._movement(lot_id, "receipt", accepted, receipt_id, day)
            if undelivered:
                update_id = f"UPD-{delivery['line_id']}-C-{day.isoformat()}"
                self.db.execute(
                    "INSERT INTO supplier_updates VALUES (?,?,?,?,?,?,?,?)",
                    (update_id, delivery["po_id"], "capacity_rejection", None, undelivered, "Warehouse capacity prevented receipt; quantity remains outstanding.", day.isoformat(), day.isoformat()),
                )
                self.pending_deliveries.append({**delivery, "date": add_workdays(day, 1), "units": undelivered})

    def _dispatch(self, day: date) -> None:
        lines = sorted(
            (line for line in self.order_lines.values() if line["remaining"] > 0 and line["due"] <= day),
            key=lambda line: (line["due"], line["created"], line["line_id"]),
        )
        for line in lines:
            customer = self.customers[line["customer_id"]]
            lots = self._eligible_lots(line["product_id"], day, customer["minimum_remaining_shelf_life_days"])
            eligible_units = sum(lot["remaining"] for lot in lots)
            if not customer["accepts_partial"] and eligible_units < line["remaining"]:
                continue
            to_ship = min(line["remaining"], eligible_units)
            for lot in lots:
                if to_ship <= 0:
                    break
                units = min(to_ship, lot["remaining"])
                self.shipment_counter += 1
                shipment_id = f"SHP-{self.shipment_counter:07d}"
                self.db.execute(
                    "INSERT INTO shipments VALUES (?,?,?,?,?,?,?)",
                    (shipment_id, line["line_id"], lot["lot_id"], units, day.isoformat(), day.isoformat(), day.isoformat()),
                )
                lot["remaining"] -= units
                line["remaining"] -= units
                to_ship -= units
                self._movement(lot["lot_id"], "shipment", -units, shipment_id, day)

    def _cancel_overdue(self, day: date) -> None:
        for line in self.order_lines.values():
            if line["remaining"] <= 0:
                continue
            customer = self.customers[line["customer_id"]]
            deadline = add_workdays(line["due"], customer["maximum_late_workdays"])
            if day < deadline:
                continue
            self.cancellation_counter += 1
            cancellation_id = f"CAN-{self.cancellation_counter:06d}"
            self.db.execute(
                "INSERT INTO cancellations VALUES (?,?,?,?,?,?,?)",
                (cancellation_id, line["line_id"], line["remaining"], "Customer delivery window ended.", day.isoformat(), day.isoformat(), day.isoformat()),
            )
            line["remaining"] = 0

    def _expire(self, day: date) -> None:
        for lot in self.lots.values():
            if lot["remaining"] > 0 and lot["expiry_date"] <= day:
                units = lot["remaining"]
                lot["remaining"] = 0
                self._movement(lot["lot_id"], "expiry", -units, lot["lot_id"], day)

    def _eligible_lots(self, product_id: str, day: date, freshness_days: int) -> list[dict]:
        threshold = day + timedelta(days=freshness_days)
        return sorted(
            (
                lot for lot in self.lots.values()
                if lot["product_id"] == product_id and lot["remaining"] > 0 and lot["expiry_date"] >= threshold
            ),
            key=lambda lot: (lot["expiry_date"], lot["received_date"], lot["lot_id"]),
        )

    def _movement(self, lot_id: str, movement_type: str, delta: int, source_id: str, day: date) -> None:
        self.movement_counter += 1
        event = day.isoformat()
        self.db.execute(
            "INSERT INTO stock_movements VALUES (?,?,?,?,?,?,?)",
            (f"MOV-{self.movement_counter:08d}", lot_id, movement_type, delta, source_id, event, event),
        )

    def _product_stock(self, product_id: str) -> int:
        return sum(lot["remaining"] for lot in self.lots.values() if lot["product_id"] == product_id)

    def _pending_product_units(self, product_id: str) -> int:
        # Read confirmed ordered less received, never hidden arrival schedules.
        return self.db.execute("""
            SELECT COALESCE(SUM(l.ordered_units - COALESCE(
                (SELECT SUM(r.received_units) FROM receipts r
                 WHERE r.supplier_order_line_id=l.supplier_order_line_id),0)),0)
            FROM supplier_order_lines l WHERE l.product_id=?
        """, (product_id,)).fetchone()[0]

    def _used_capacity_ml(self) -> int:
        return sum(lot["remaining"] * self.products[lot["product_id"]]["storage_ml_per_unit"] for lot in self.lots.values())

    def _weekly_budget(self) -> int:
        return self.config.effective_budget_cents

    def _write_closing_stock(self, as_of: date) -> None:
        for lot in self.lots.values():
            self.db.execute(
                "INSERT INTO closing_stock VALUES (?,?,?)",
                (lot["lot_id"], lot["remaining"], as_of.isoformat()),
            )
