"""Configuration parameters, audit benchmarks, and grid specifications for Phase 5 simulation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class SimulationConfig:
    """Immutable configuration container for historical simulation and sensitivity analysis."""

    # Project paths
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    artifacts_dir: Path = project_root / "artifacts"
    daily_onhand_parquet_path: Path = artifacts_dir / "daily_onhand.parquet"
    demand_parquet_path: Path = artifacts_dir / "demand.parquet"
    policy_parquet_path: Path = artifacts_dir / "policy.parquet"

    # Artifact outputs
    simulation_report_path: Path = artifacts_dir / "simulation_report.md"
    simulation_results_parquet_path: Path = artifacts_dir / "simulation_results.parquet"

    # Timeline constants (Anti-leakage boundaries)
    start_date: str = "2025-06-01"
    end_date: str = "2026-04-24"
    total_days: int = 328

    # Default policy parameters
    default_lead_time_days: int = 10
    default_service_level: float = 0.95
    default_annual_holding_rate: float = 0.20
    default_reorder_cost_fixed: float = 50.0
    default_reorder_cost_line: float = 2.0
    default_min_order_qty: int = 5
    default_stocking_demand_threshold: float = 0.004
    baseline_replenishment_orders: int = 13038  # Verified store delivery receipts in raw ledger

    # Sensitivity grid specifications (3 x 3 x 3 = 27 runs)
    lead_time_grid: Tuple[int, ...] = (5, 10, 15)
    service_level_grid: Tuple[float, ...] = (0.90, 0.95, 0.98)
    holding_rate_grid: Tuple[float, ...] = (0.15, 0.20, 0.25)

    # Known audit benchmarks from BUSINESS_CONTEXT.md & OPTIMISER_LOGIC.md
    audit_avg_standing_stock_eur: float = 2404541.94  # ~$2.4M standing stock
    audit_annual_turnover: float = 2.71               # 2.71x per year
    audit_days_sales_inventory: float = 134.9         # 134.9 days


DEFAULT_SIMULATION_CONFIG = SimulationConfig()
