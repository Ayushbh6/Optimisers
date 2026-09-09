"""Phase 2: True (Unconstrained) Demand Estimation Module.

Exports core functions and configurations for stockout censoring detection,
hierarchical unconstrained demand estimation, and invariant validation.
"""

from src.demand.config import DemandConfig, DEFAULT_DEMAND_CONFIG
from src.demand.censoring import (
    aggregate_daily_sales,
    identify_censoring,
    align_sales_and_inventory,
)
from src.demand.unconstraining import (
    extract_product_hierarchy,
    compute_in_stock_demand_rates,
    estimate_unconstrained_demand,
)
from src.demand.validator import (
    validate_alignment,
    validate_censoring,
    validate_uplift,
    validate_non_negativity,
    validate_phase2_all,
)

__all__ = [
    "DemandConfig",
    "DEFAULT_DEMAND_CONFIG",
    "aggregate_daily_sales",
    "identify_censoring",
    "align_sales_and_inventory",
    "extract_product_hierarchy",
    "compute_in_stock_demand_rates",
    "estimate_unconstrained_demand",
    "validate_alignment",
    "validate_censoring",
    "validate_uplift",
    "validate_non_negativity",
    "validate_phase2_all",
]
