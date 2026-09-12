"""Phase 5: Walk-Forward Historical Simulation Module.

Exports simulation models, baseline evaluation, sensitivity sweep, and reporting tools.
"""

from src.simulation.config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from src.simulation.metrics import SimulationMetrics, compute_simulation_metrics
from src.simulation.baseline import evaluate_observed_historical_baseline
from src.simulation.engine import run_walkforward_simulation
from src.simulation.sensitivity import run_sensitivity_sweep, recompute_policy_for_scenario
from src.simulation.report import generate_simulation_report
from src.simulation.validator import (
    validate_walkforward,
    validate_non_negativity,
    validate_baseline_reproduction,
    validate_service_level_guard,
    validate_ordering_cost_netting,
    validate_unified_service_level,
)
from src.simulation.replay import (
    DailyReplayInput,
    ForecastContext,
    ForecastSnapshot,
    InitialPairState,
    ObservableHistory,
    PolicyContext,
    ReplayCostAssumptions,
    ReplayMetrics,
    ReplayResult,
    run_causal_replay,
)

__all__ = [
    "SimulationConfig",
    "DEFAULT_SIMULATION_CONFIG",
    "SimulationMetrics",
    "compute_simulation_metrics",
    "evaluate_observed_historical_baseline",
    "run_walkforward_simulation",
    "run_sensitivity_sweep",
    "recompute_policy_for_scenario",
    "generate_simulation_report",
    "validate_walkforward",
    "validate_non_negativity",
    "validate_baseline_reproduction",
    "validate_service_level_guard",
    "validate_ordering_cost_netting",
    "validate_unified_service_level",
    "DailyReplayInput",
    "ForecastContext",
    "ForecastSnapshot",
    "InitialPairState",
    "ObservableHistory",
    "PolicyContext",
    "ReplayCostAssumptions",
    "ReplayMetrics",
    "ReplayResult",
    "run_causal_replay",
]
