"""Configuration parameters, assumptions, and schema for Phase 4 inventory policy."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PolicyConfig:
    """Immutable configuration container for (s, S) inventory policy engine.

    All operational parameters and economic assumptions are explicit, user-configurable,
    and persisted directly into the resulting policy artifact for auditability.
    """

    # Project paths
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    artifacts_dir: Path = project_root / "artifacts"
    forecast_parquet_path: Path = artifacts_dir / "forecast.parquet"
    daily_onhand_parquet_path: Path = artifacts_dir / "daily_onhand.parquet"
    policy_parquet_path: Path = artifacts_dir / "policy.parquet"

    # Explicit Operational Assumptions (PLAN.md defaults)
    supplier_lead_time_days: int = 10         # Days between PO issuance and store shelf receipt
    target_service_level: float = 0.95        # Cycle service level (95%)
    annual_holding_cost_rate: float = 0.20    # Holding cost as % of unit cost per year (20%)
    reorder_cost_fixed: float = 50.0          # Fixed replenishment delivery cost per event (€50)
    reorder_cost_line_item: float = 2.0       # Marginal order cost allocated per SKU line item (€2)
    min_order_quantity: int = 5               # Minimum order quantity (MOQ = 5 units per PLAN.md)
    stocking_demand_threshold: float = 0.004  # Minimum daily velocity to justify stocking shelf (~1.5 units/yr)

    # Observed baseline benchmark for capital sanity check
    observed_inventory_baseline_eur: float = 2404541.94  # Audit standing stock benchmark

    # Output schema definition
    policy_columns: tuple = (
        "Product No",
        "Store",
        "reorder_point_s",
        "order_up_to_S",
        "safety_stock",
        "order_qty_q",
        "target_stock",
        "unit_cost",
        "daily_expected_demand",
        "lead_time_days",
        "target_service_level",
        "annual_holding_rate",
        "reorder_cost",
        "min_order_qty",
    )


DEFAULT_POLICY_CONFIG = PolicyConfig()
