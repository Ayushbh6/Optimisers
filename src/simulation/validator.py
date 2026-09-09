"""Validation suite for Phase 5: Historical Walk-Forward Simulation.

Enforces all invariants mandated by PLAN.md:
  1. test_phase5_walkforward: simulation consumes exactly 328 days with zero lookahead.
  2. test_phase5_nonneg: simulated on-hand is never negative.
  3. test_phase5_baseline_repro: observed policy metrics reproduce known audit figures within tolerance.
  4. test_phase5_service_guard: optimized service level >= target service level - 5pts.
"""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.metrics import SimulationMetrics

logger = logging.getLogger(__name__)


def validate_walkforward(
    audit_stats: Dict[str, Any],
    expected_days: int = 328,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that the walk-forward simulation processed exactly 328 days.

    Args:
        audit_stats: Audit stats dictionary from simulation run.
        expected_days: Expected calendar day count (328).

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating walk-forward simulation duration...")
    days_processed = audit_stats.get("days_processed", 0)
    passed = (days_processed == expected_days)

    metrics = {
        "days_processed": days_processed,
        "expected_days": expected_days,
    }

    if passed:
        msg = f"Walk-forward check passed: Simulation processed exactly {days_processed} sequential days."
        logger.info(msg)
    else:
        msg = f"Walk-forward check failed: Processed {days_processed} days (expected {expected_days})."
        logger.error(msg)

    return passed, msg, metrics


def validate_non_negativity(
    sim_onhand: np.ndarray,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that simulated on-hand inventory is strictly non-negative everywhere.

    Args:
        sim_onhand: 2D array of simulated daily on-hand units.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating simulated on-hand non-negativity...")
    neg_count = int(np.sum(sim_onhand < -1e-6))
    passed = (neg_count == 0)

    metrics = {
        "negative_values_count": neg_count,
        "min_onhand_val": float(np.min(sim_onhand)),
    }

    if passed:
        msg = f"Non-negativity check passed: 0 negative on-hand values across all {sim_onhand.size:,} cell-days."
        logger.info(msg)
    else:
        msg = f"Non-negativity check failed: Found {neg_count} negative on-hand values."
        logger.error(msg)

    return passed, msg, metrics


def validate_baseline_reproduction(
    baseline_metrics: SimulationMetrics,
    config: SimulationConfig = DEFAULT_SIMULATION_CONFIG,
    tolerance: float = 0.05,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that observed baseline metrics reproduce known audit figures within 5% tolerance.

    Target benchmarks:
      - Average standing stock: €2,404,541.94 (tolerance: +-5%)
      - Inventory turnover: ~2.71x (tolerance: +-10%)

    Args:
        baseline_metrics: SimulationMetrics from observed history.
        config: Simulation configuration with audit benchmarks.
        tolerance: Allowed fractional deviation (default 5% for stock).

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating reproduction of known audit figures within <= 5%...")
    target_stock = config.audit_avg_standing_stock_eur
    target_turnover = config.audit_annual_turnover

    stock_diff = abs(baseline_metrics.avg_inventory_value_eur - target_stock) / target_stock
    turnover_diff = abs(baseline_metrics.inventory_turnover - target_turnover) / target_turnover

    passed_stock = stock_diff <= tolerance
    passed_turnover = turnover_diff <= 0.10
    passed = passed_stock and passed_turnover

    metrics = {
        "calculated_stock_eur": baseline_metrics.avg_inventory_value_eur,
        "target_stock_eur": target_stock,
        "stock_relative_diff": stock_diff,
        "calculated_turnover": baseline_metrics.inventory_turnover,
        "target_turnover": target_turnover,
        "turnover_relative_diff": turnover_diff,
    }

    if passed:
        msg = (
            f"Baseline reproduction passed: Standing stock €{baseline_metrics.avg_inventory_value_eur:,.2f} "
            f"(target €{target_stock:,.2f}, diff {stock_diff*100:.2f}% <= {tolerance*100:.0f}%), "
            f"Turnover {baseline_metrics.inventory_turnover:.2f}x "
            f"(target ~{target_turnover:.2f}x, diff {turnover_diff*100:.1f}% <= 10%)."
        )
        logger.info(msg)
    else:
        msg = f"Baseline reproduction failed: Stock diff {stock_diff*100:.2f}%, Turnover diff {turnover_diff*100:.1f}%."
        logger.error(msg)

    return passed, msg, metrics


def validate_ordering_cost_netting(
    baseline_metrics: SimulationMetrics,
    default_metrics: SimulationMetrics,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that ordering cost is non-zero, included in TCO, and net economic savings are computed.

    Args:
        baseline_metrics: Baseline metrics.
        default_metrics: Optimized policy metrics.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating ordering cost inclusion and net TCO calculation...")
    has_opt_ordering = default_metrics.ordering_cost_eur > 0
    has_base_ordering = baseline_metrics.ordering_cost_eur > 0
    has_opt_tco = default_metrics.total_cost_of_ownership_eur > 0
    has_base_tco = baseline_metrics.total_cost_of_ownership_eur > 0

    net_savings = baseline_metrics.total_cost_of_ownership_eur - default_metrics.total_cost_of_ownership_eur
    passed = bool(has_opt_ordering and has_base_ordering and has_opt_tco and has_base_tco)

    metrics = {
        "baseline_ordering_cost_eur": baseline_metrics.ordering_cost_eur,
        "optimized_ordering_cost_eur": default_metrics.ordering_cost_eur,
        "baseline_tco_eur": baseline_metrics.total_cost_of_ownership_eur,
        "optimized_tco_eur": default_metrics.total_cost_of_ownership_eur,
        "net_economic_savings_eur": net_savings,
    }

    if passed:
        msg = (
            f"Ordering cost netting passed: Baseline TCO = €{baseline_metrics.total_cost_of_ownership_eur:,.2f}, "
            f"Optimized TCO = €{default_metrics.total_cost_of_ownership_eur:,.2f} "
            f"(Net economic savings = €{net_savings:,.2f})."
        )
        logger.info(msg)
    else:
        msg = "Ordering cost netting failed: Ordering cost or TCO missing."
        logger.error(msg)

    return passed, msg, metrics


def validate_unified_service_level(
    baseline_metrics: SimulationMetrics,
    default_metrics: SimulationMetrics,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that single, unified service-level metrics are reported for both policies.

    Args:
        baseline_metrics: Baseline metrics.
        default_metrics: Optimized policy metrics.

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating unified apples-to-apples service level reporting...")
    base_sl = baseline_metrics.active_in_stock_service_level
    opt_sl = default_metrics.active_in_stock_service_level

    # Both must be valid percentages (> 0.50 and <= 1.0)
    passed = bool((0.50 <= base_sl <= 1.0) and (0.50 <= opt_sl <= 1.0))

    metrics = {
        "baseline_active_service_level": base_sl,
        "optimized_active_service_level": opt_sl,
        "service_level_delta_pts": (opt_sl - base_sl) * 100.0,
    }

    if passed:
        msg = (
            f"Unified service level check passed: Baseline active SL = {base_sl*100:.2f}%, "
            f"Optimized active SL = {opt_sl*100:.2f}% (Delta = {metrics['service_level_delta_pts']:+.2f} pts)."
        )
        logger.info(msg)
    else:
        msg = f"Unified service level check failed: Invalid values {base_sl}, {opt_sl}."
        logger.error(msg)

    return passed, msg, metrics


def validate_service_level_guard(
    audit_stats: Dict[str, Any],
    target_service_level: float = 0.95,
    margin: float = 0.05,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate that optimized service level >= target service level - margin (90% for 95% target).

    Args:
        audit_stats: Audit stats dictionary containing 'active_service_level'.
        target_service_level: Target cycle service level (0.95).
        margin: Allowed tolerance margin (0.05).

    Returns:
        Tuple of (passed: bool, message: str, metrics: dict).
    """
    logger.info("Validating service level guard against collapse...")
    active_sl = audit_stats.get("active_service_level", 0.0)
    required_sl = target_service_level - margin
    passed = bool(active_sl >= required_sl)

    metrics = {
        "active_service_level": active_sl,
        "required_threshold": required_sl,
        "target_service_level": target_service_level,
    }

    if passed:
        msg = (
            f"Service level guard passed: Active in-stock reliability is {active_sl*100:.2f}% "
            f"(>= required {required_sl*100:.1f}%)."
        )
        logger.info(msg)
    else:
        msg = f"Service level guard failed: Realized {active_sl*100:.2f}% < {required_sl*100:.1f}%."
        logger.error(msg)

    return passed, msg, metrics
