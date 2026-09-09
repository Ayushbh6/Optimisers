"""Vectorized walk-forward historical simulation engine.

Simulates 328 days of retail store operations under (s, S) replenishment rules
with strict anti-leakage boundaries, pipeline order tracking, and lost-sales modeling.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.metrics import SimulationMetrics, compute_simulation_metrics

logger = logging.getLogger(__name__)


def run_walkforward_simulation(
    arrays: Dict[str, Any],
    s_arr: np.ndarray,
    S_arr: np.ndarray,
    lead_time_days: int = 10,
    holding_cost_rate: float = 0.20,
    target_service_level: float = 0.95,
    reorder_cost_fixed: float = 50.0,
) -> Tuple[SimulationMetrics, np.ndarray, np.ndarray, Dict[str, Any]]:
    """Execute chronological 328-day walk-forward simulation across all pairs.

    Anti-leakage rules:
      - Chronological day-by-day progression: t = 0 ... 327.
      - Decisions on day t use strictly information available on/before day t.
      - Pipeline arrival: Orders placed on day t arrive on day t + lead_time.
      - Lost sales: When demand exceeds shelf on-hand, unmet demand is lost.

    Args:
        arrays: Dictionary containing preprocessed simulation arrays from baseline.py.
        s_arr: 1D array of reorder points per pair.
        S_arr: 1D array of order-up-to levels per pair.
        lead_time_days: Supplier lead time in calendar days.
        holding_cost_rate: Annual holding cost rate.
        target_service_level: Target cycle service level.
        reorder_cost_fixed: Fixed cost per store replenishment delivery event (€).

    Returns:
        Tuple of (SimulationMetrics, sim_onhand_history, sim_sales_history, audit_stats).
    """
    pivot_demand = arrays["pivot_demand"]
    pivot_onhand = arrays["pivot_onhand"]
    unit_costs = arrays["unit_costs"]
    n_days, n_pairs = pivot_demand.shape

    first_idx_arr = arrays.get("first_idx_arr")
    last_idx_arr = arrays.get("last_idx_arr")
    if first_idx_arr is None or last_idx_arr is None:
        has_pos = (pivot_onhand > 0)
        first_idx_arr = np.where(has_pos.any(axis=0), has_pos.argmax(axis=0), n_days).astype(np.int32)
        last_idx_arr = np.where(has_pos.any(axis=0), n_days - 1 - has_pos[::-1].argmax(axis=0), n_days).astype(np.int32)

    # Stocking eligibility (items with positive order-up-to level)
    is_stocked = (S_arr > 0)

    # Map pairs to store indices for store delivery PO tracking
    pair_cols = arrays.get("pair_columns")
    if pair_cols is not None:
        store_names = [s for p, s in pair_cols]
        unique_stores = sorted(list(set(store_names)))
        store_indices = {s: np.where(np.array(store_names) == s)[0] for s in unique_stores}
    else:
        store_indices = {0: np.arange(n_pairs)}

    # 2. State initialization at Day 0 (2025-06-01)
    curr_onhand = pivot_onhand[0].copy()
    pipeline = np.zeros((lead_time_days, n_pairs), dtype=np.float32)

    sim_onhand = np.zeros((n_days, n_pairs), dtype=np.float32)
    sim_sales = np.zeros((n_days, n_pairs), dtype=np.float32)
    total_sku_orders = 0
    total_store_pos = 0

    active_in_stock_days = 0
    active_stockout_days = 0

    # 3. Chronological day-by-day simulation loop
    for t in range(n_days):
        # A. Pipeline order delivery arrival
        arrivals = pipeline[0]
        curr_onhand += arrivals

        # B. New product introductions on day t (receive initial shelf inventory)
        newly_introduced = (first_idx_arr == t) & (curr_onhand == 0) & is_stocked
        curr_onhand += np.where(newly_introduced, np.minimum(pivot_onhand[t], S_arr), 0.0)

        # C. Advance order pipeline
        pipeline[:-1] = pipeline[1:]
        pipeline[-1] = 0.0

        # D. Customer demand fulfillment and lost sales
        demand_today = pivot_demand[t]
        sales_today = np.minimum(curr_onhand, demand_today)
        curr_onhand = np.maximum(curr_onhand - sales_today, 0.0)

        sim_onhand[t] = curr_onhand
        sim_sales[t] = sales_today

        # E. Track active assortment service level
        active_today = (first_idx_arr <= t) & (t <= last_idx_arr) & is_stocked
        active_in_stock_days += int(np.sum(active_today & (curr_onhand > 0)))
        active_stockout_days += int(np.sum(active_today & (curr_onhand == 0)))

        # F. Continuous-review inventory position review and replenishment
        on_order = np.sum(pipeline, axis=0)
        inv_position = curr_onhand + on_order
        needs_order = (inv_position <= s_arr) & active_today
        order_qty = np.where(needs_order, np.maximum(S_arr - inv_position, 0.0), 0.0)

        pipeline[lead_time_days - 1] += order_qty
        total_sku_orders += int(np.sum(needs_order))

        # G. Track store replenishment delivery PO events
        for s_idx in store_indices.values():
            if np.any(needs_order[s_idx]):
                total_store_pos += 1

    tot_active_days = active_in_stock_days + active_stockout_days
    active_service_level = (
        float(active_in_stock_days / tot_active_days) if tot_active_days > 0 else 1.0
    )

    # 4. Compute standardized simulation metrics
    metrics = compute_simulation_metrics(
        daily_onhand_history=sim_onhand,
        daily_sales_history=sim_sales,
        daily_demand_history=pivot_demand,
        unit_costs=unit_costs,
        holding_cost_rate=holding_cost_rate,
        reorder_cost_fixed=reorder_cost_fixed,
        orders_count=total_store_pos,
        active_in_stock_days=active_in_stock_days,
        total_active_days=tot_active_days,
    )

    audit_stats = {
        "days_processed": n_days,
        "lead_time_days": lead_time_days,
        "target_service_level": target_service_level,
        "active_service_level": active_service_level,
        "active_in_stock_days": active_in_stock_days,
        "active_stockout_days": active_stockout_days,
        "total_store_po_orders": total_store_pos,
        "total_sku_order_triggers": total_sku_orders,
    }

    return metrics, sim_onhand, sim_sales, audit_stats
