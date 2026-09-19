"""Load public records without connecting to evaluator storage."""
from datetime import date, timedelta
from pathlib import Path

from src.demo_data.snapshot import snapshot
from src.demo_data.schema import connect
from .contracts import Customer, Demand, Incoming, Lot, PlanningSnapshot, Product, Supplier, Term


def load_snapshot(path: Path, as_of: date, *, phase: str = 'end_of_day') -> PlanningSnapshot:
    """Load an end-of-day anchor or the actual before-ordering decision boundary."""
    rows = snapshot(path, as_of, phase=phase)
    with connect(path, readonly=True) as db:
        history_start = date.fromisoformat(db.execute(
            "SELECT value FROM dataset_manifest WHERE key = 'history_start'").fetchone()[0])
    products = {r['product_id']: Product(r['product_id'], r['name'], r['case_size_units'],
                r['storage_ml_per_unit'], r['normal_shelf_life_days']) for r in rows['products']}
    suppliers = {r['supplier_id']: Supplier(r['supplier_id'], r['order_weekday'],
                 r['standard_lead_workdays'], r['minimum_order_value_cents'], r['delivery_charge_cents'])
                 for r in rows['suppliers']}
    customers = {r['customer_id']: Customer(r['customer_id'], bool(r['accepts_partial']),
                 r['maximum_late_workdays'], r['minimum_remaining_shelf_life_days']) for r in rows['customers']}
    terms = [Term(r['supplier_id'], r['product_id'], r['purchase_cost_cents'], r['minimum_order_units'],
                  date.fromisoformat(r['effective_from']),
                  date.fromisoformat(r['effective_to']) if r['effective_to'] else None)
             for r in rows['supplier_product_terms']]
    balances = {r['lot_id']: r['quantity_units'] for r in rows['snapshot_stock']}
    lots = {r['lot_id']: Lot(r['lot_id'], r['product_id'], date.fromisoformat(r['received_date']),
            date.fromisoformat(r['expiry_date']), r['acquisition_cost_cents'], balances.get(r['lot_id'], 0))
            for r in rows['stock_lots'] if balances.get(r['lot_id'], 0)}
    headers = {r['customer_order_id']: r for r in rows['customer_orders']}
    demand = {}
    for r in rows['customer_order_lines']:
        h = headers[r['customer_order_id']]
        demand[r['customer_order_line_id']] = Demand(r['customer_order_line_id'], r['product_id'],
            h['customer_id'], date.fromisoformat(h['created_date']), date.fromisoformat(h['due_date']),
            r['requested_units'], r['shipped_units'], r['cancelled_units'])
    for shipment in rows['shipments']:
        line = demand[shipment['customer_order_line_id']]
        if date.fromisoformat(shipment['dispatch_date']) <= line.due:
            line.on_time += shipment['shipped_units']
    pos = {r['supplier_order_id']: r for r in rows['supplier_orders']}
    incoming = {}
    for r in rows['supplier_order_lines']:
        if not r['outstanding_units']:
            continue
        h = pos[r['supplier_order_id']]
        expected = h['expected_delivery_date']
        for update in sorted(rows['supplier_updates'], key=lambda x: (x['known_at'], x['supplier_update_id'])):
            if update['supplier_order_id'] == h['supplier_order_id'] and update['revised_expected_date']:
                expected = update['revised_expected_date']
        incoming[r['supplier_order_line_id']] = Incoming(r['supplier_order_line_id'], h['supplier_order_id'],
            h['supplier_id'], r['product_id'], date.fromisoformat(h['placed_date']),
            date.fromisoformat(expected), r['ordered_units'], r['unit_cost_cents'], r['received_units'])
    limits = [r for r in rows['planning_limits'] if r['effective_from'] <= as_of.isoformat()
              and (r['effective_to'] is None or r['effective_to'] >= as_of.isoformat())]
    if len(limits) != 1:
        raise ValueError('Expected one active planning limit')
    monday = as_of - timedelta(days=as_of.weekday())
    week_pos = {key for key, h in pos.items() if h['placed_date'] >= monday.isoformat()}
    spend = sum(r['ordered_units'] * r['unit_cost_cents'] for r in rows['supplier_order_lines']
                if r['supplier_order_id'] in week_pos)
    spend += sum(pos[key]['delivery_charge_cents'] for key in week_pos)
    return PlanningSnapshot(as_of, products, suppliers, customers, terms, lots, demand, incoming,
                            limits[0]['weekly_new_order_budget_cents'], limits[0]['warehouse_capacity_ml'],
                            spend, notices=rows['supplier_updates'], promotions=rows['promotions'],
                            request_history_start=history_start)
