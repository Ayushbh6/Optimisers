"""Standardized metric evaluation calculators for inventory simulations and historical baselines."""

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass(frozen=True)
class SimulationMetrics:
    """Immutable container holding uniform inventory performance metrics."""

    avg_inventory_value_eur: float
    total_demand_units: float
    total_sales_units: float
    total_lost_sales_units: float
    fill_rate_service_level: float
    active_in_stock_service_level: float
    stockout_pair_days: int
    total_pair_days: int
    stockout_rate: float
    annual_cogs_eur: float
    inventory_turnover: float
    days_sales_inventory: float
    holding_cost_eur: float
    ordering_cost_eur: float
    total_cost_of_ownership_eur: float
    total_orders_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "avg_inventory_value_eur": self.avg_inventory_value_eur,
            "total_demand_units": self.total_demand_units,
            "total_sales_units": self.total_sales_units,
            "total_lost_sales_units": self.total_lost_sales_units,
            "fill_rate_service_level": self.fill_rate_service_level,
            "active_in_stock_service_level": self.active_in_stock_service_level,
            "stockout_pair_days": self.stockout_pair_days,
            "total_pair_days": self.total_pair_days,
            "stockout_rate": self.stockout_rate,
            "annual_cogs_eur": self.annual_cogs_eur,
            "inventory_turnover": self.inventory_turnover,
            "days_sales_inventory": self.days_sales_inventory,
            "holding_cost_eur": self.holding_cost_eur,
            "ordering_cost_eur": self.ordering_cost_eur,
            "total_cost_of_ownership_eur": self.total_cost_of_ownership_eur,
            "total_orders_count": self.total_orders_count,
        }


def compute_simulation_metrics(
    daily_onhand_history: np.ndarray,      # shape (n_days, n_pairs)
    daily_sales_history: np.ndarray,       # shape (n_days, n_pairs)
    daily_demand_history: np.ndarray,      # shape (n_days, n_pairs)
    unit_costs: np.ndarray,                # shape (n_pairs,)
    holding_cost_rate: float = 0.20,
    reorder_cost_fixed: float = 50.0,
    orders_count: int = 0,
    active_in_stock_days: int = 0,
    total_active_days: int = 0,
) -> SimulationMetrics:
    """Compute uniform inventory metrics from daily arrays.

    Args:
        daily_onhand_history: 2D array of on-hand units per day per pair.
        daily_sales_history: 2D array of satisfied sales units per day per pair.
        daily_demand_history: 2D array of true unconstrained demand units per day per pair.
        unit_costs: 1D array of wholesale unit cost per pair.
        holding_cost_rate: Annual holding rate (default 0.20).
        reorder_cost_fixed: Fixed replenishment cost per order (default 50.0).
        orders_count: Total replenishment orders placed.
        active_in_stock_days: Total active in-stock pair-days.
        total_active_days: Total active pair-days.

    Returns:
        SimulationMetrics instance.
    """
    n_days, n_pairs = daily_onhand_history.shape
    total_pair_days = n_days * n_pairs

    # 1. Daily inventory value = on_hand * unit_cost summed across pairs
    daily_inv_value = np.sum(daily_onhand_history * unit_costs, axis=1)
    avg_inv_val = float(np.mean(daily_inv_value))

    # 2. Demand, sales, lost sales
    tot_demand = float(np.sum(daily_demand_history))
    tot_sales = float(np.sum(daily_sales_history))
    tot_lost_sales = max(0.0, tot_demand - tot_sales)

    fill_rate = float(tot_sales / tot_demand) if tot_demand > 0 else 1.0

    # 3. Active in-stock availability (apples-to-apples service level)
    active_service_level = (
        float(active_in_stock_days / total_active_days)
        if total_active_days > 0
        else fill_rate
    )

    # 4. Stockout statistics across full calendar matrix
    zero_stock_mask = (daily_onhand_history <= 0)
    stockout_days = int(np.sum(zero_stock_mask))
    stockout_rate = float(stockout_days / total_pair_days) if total_pair_days > 0 else 0.0

    # 5. COGS and Turnover (annualized across 365 days from the 328-day timeline)
    total_cogs_sample = float(np.sum(daily_sales_history * unit_costs))
    annual_cogs = total_cogs_sample * (365.0 / n_days) if n_days > 0 else 0.0

    turnover = float(annual_cogs / avg_inv_val) if avg_inv_val > 0 else 0.0
    dsi = float(365.0 / turnover) if turnover > 0 else 0.0

    # 6. Economic Cost of Ownership: Holding Cost + Ordering Cost
    holding_cost = float(holding_cost_rate * avg_inv_val * (n_days / 365.0))
    ordering_cost = float(orders_count * reorder_cost_fixed)
    total_tco = holding_cost + ordering_cost

    return SimulationMetrics(
        avg_inventory_value_eur=avg_inv_val,
        total_demand_units=tot_demand,
        total_sales_units=tot_sales,
        total_lost_sales_units=tot_lost_sales,
        fill_rate_service_level=fill_rate,
        active_in_stock_service_level=active_service_level,
        stockout_pair_days=stockout_days,
        total_pair_days=total_pair_days,
        stockout_rate=stockout_rate,
        annual_cogs_eur=annual_cogs,
        inventory_turnover=turnover,
        days_sales_inventory=dsi,
        holding_cost_eur=holding_cost,
        ordering_cost_eur=ordering_cost,
        total_cost_of_ownership_eur=total_tco,
        total_orders_count=orders_count,
    )
