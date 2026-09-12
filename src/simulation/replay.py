"""Causal historical replay primitives.

This module is deliberately independent from the original vectorised Phase 5
engine.  It provides the small, explicit replay contract needed by the repaired
pipeline:

    opening stock -> arrivals -> recorded purchases -> day-end returns
    -> closing stock -> forecast/policy decision

The forecast callback receives an observation history containing only fulfilled
purchases and availability.  It never receives the recorded target, returns,
or any future record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Callable, Hashable, Mapping, Optional, Sequence, Tuple

import math
import pandas as pd


Pair = Hashable


def _as_date(value: Any) -> date:
    """Convert a supported date-like value to a calendar date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        converted = pd.Timestamp(value)
    except Exception as exc:  # pragma: no cover - defensive error path
        raise TypeError(f"Unsupported date value: {value!r}") from exc
    if pd.isna(converted):
        raise ValueError("Dates must not be missing")
    return converted.date()


def _whole_units(value: Any, *, name: str, allow_none: bool = False) -> Optional[int]:
    """Validate a physical quantity and return it as a non-negative integer."""
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a whole, non-negative number")
    if not math.isfinite(float(value)) or float(value) < 0 or float(value) != math.floor(float(value)):
        raise ValueError(f"{name} must be a whole, non-negative number")
    return int(value)


def _money(value: Any, *, name: str) -> float:
    """Validate a finite non-negative monetary value."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite, non-negative number")
    if not math.isfinite(float(value)) or float(value) < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")
    return float(value)


@dataclass(frozen=True)
class InitialPairState:
    """Opening state for one product-store pair.

    ``on_hand=None`` means that no usable causal stock anchor exists.  Such a
    pair is retained in the ledger for transparency but is excluded from
    service and inventory comparisons until an upstream initializer supplies a
    usable anchor.
    """

    on_hand: Optional[int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "on_hand",
            _whole_units(self.on_hand, name="on_hand", allow_none=True),
        )


@dataclass(frozen=True)
class DailyReplayInput:
    """One day of recorded gross purchases and separate day-end returns."""

    day: date
    gross_purchases: Mapping[Pair, int] = field(default_factory=dict)
    returns: Mapping[Pair, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "day", _as_date(self.day))
        object.__setattr__(
            self,
            "gross_purchases",
            MappingProxyType({
                pair: _whole_units(qty, name=f"gross_purchases[{pair!r}]")
                for pair, qty in self.gross_purchases.items()
            }),
        )
        object.__setattr__(
            self,
            "returns",
            MappingProxyType({
                pair: _whole_units(qty, name=f"returns[{pair!r}]")
                for pair, qty in self.returns.items()
            }),
        )


@dataclass(frozen=True)
class ForecastSnapshot:
    """A forecast supplied to a policy for one pair at one decision time."""

    expected_demand_units: float
    horizon_days: int = 1
    method: str = "unspecified"
    uncertainty_label: str = "unreported"

    def __post_init__(self) -> None:
        if isinstance(self.expected_demand_units, bool) or not isinstance(self.expected_demand_units, Real):
            raise TypeError("expected_demand_units must be a finite, non-negative number")
        if not math.isfinite(float(self.expected_demand_units)) or float(self.expected_demand_units) < 0:
            raise ValueError("expected_demand_units must be a finite, non-negative number")
        horizon = _whole_units(self.horizon_days, name="horizon_days")
        if horizon == 0:
            raise ValueError("horizon_days must be at least one day")
        object.__setattr__(self, "horizon_days", horizon)
        object.__setattr__(self, "expected_demand_units", float(self.expected_demand_units))


@dataclass(frozen=True)
class ObservableHistory:
    """What the simulated shop has observed by a decision date.

    The two histories intentionally contain fulfilled purchases and shelf
    availability only.  Recorded targets, unfulfilled units and returns are
    not exposed to forecasting code.
    """

    as_of: date
    dates: Tuple[date, ...]
    fulfilled_purchases: Mapping[Pair, Tuple[int, ...]]
    availability: Mapping[Pair, Tuple[bool, ...]]


@dataclass(frozen=True)
class ForecastContext:
    """Input passed to the forecast snapshot provider."""

    as_of: date
    history: ObservableHistory


@dataclass(frozen=True)
class PolicyContext:
    """Causal state passed to the optional reorder policy callback."""

    as_of: date
    closing_on_hand: Mapping[Pair, int]
    on_order: Mapping[Pair, int]
    inventory_position: Mapping[Pair, int]
    costs: Mapping[Pair, Optional[float]]
    forecasts: Mapping[Pair, ForecastSnapshot]
    history: ObservableHistory


@dataclass(frozen=True)
class ReplayCostAssumptions:
    """Explicit assumptions used for scenario accounting.

    There are no defaults because a replay cannot invent historical purchase
    costs.  Fixed and line costs apply to pair-level orders produced by the
    callback; a later integration can aggregate those orders into store POs.
    """

    annual_holding_rate: Optional[float] = None
    fixed_order_cost_eur: Optional[float] = None
    line_order_cost_eur: Optional[float] = None
    annual_days: int = 365

    def __post_init__(self) -> None:
        if self.annual_holding_rate is not None:
            if not isinstance(self.annual_holding_rate, Real) or isinstance(self.annual_holding_rate, bool):
                raise TypeError("annual_holding_rate must be a finite, non-negative number")
            if not math.isfinite(float(self.annual_holding_rate)) or float(self.annual_holding_rate) < 0:
                raise ValueError("annual_holding_rate must be a finite, non-negative number")
            object.__setattr__(self, "annual_holding_rate", float(self.annual_holding_rate))
        for field_name in ("fixed_order_cost_eur", "line_order_cost_eur"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _money(value, name=field_name))
        days = _whole_units(self.annual_days, name="annual_days")
        if days == 0:
            raise ValueError("annual_days must be at least one day")
        object.__setattr__(self, "annual_days", days)


@dataclass(frozen=True)
class ReplayMetrics:
    """Metrics from one replay, with scope and cost coverage made explicit."""

    total_target_units: int
    total_fulfilled_units: int
    total_unfulfilled_units: int
    observed_purchase_coverage: Optional[float]
    eligible_pair_days: int
    available_pair_days: int
    availability_rate: Optional[float]
    ending_on_hand_units: int
    total_order_units: int
    total_order_events: int
    average_inventory_value_eur: Optional[float]
    average_daily_inventory_value_eur: Optional[float]
    valued_pair_days: int
    inventory_pair_days: int
    inventory_cost_coverage: float
    holding_cost_eur: Optional[float]
    ordering_cost_eur: Optional[float]
    total_cost_of_ownership_eur: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON/parquet-friendly metric names."""
        return {
            "total_target_units": self.total_target_units,
            "total_fulfilled_units": self.total_fulfilled_units,
            "total_unfulfilled_units": self.total_unfulfilled_units,
            "observed_purchase_coverage": self.observed_purchase_coverage,
            "eligible_pair_days": self.eligible_pair_days,
            "available_pair_days": self.available_pair_days,
            "availability_rate": self.availability_rate,
            "ending_on_hand_units": self.ending_on_hand_units,
            "total_order_units": self.total_order_units,
            "total_order_events": self.total_order_events,
            "average_inventory_value_eur": self.average_inventory_value_eur,
            "average_daily_inventory_value_eur": self.average_daily_inventory_value_eur,
            "valued_pair_days": self.valued_pair_days,
            "inventory_pair_days": self.inventory_pair_days,
            "inventory_cost_coverage": self.inventory_cost_coverage,
            "holding_cost_eur": self.holding_cost_eur,
            "ordering_cost_eur": self.ordering_cost_eur,
            "total_cost_of_ownership_eur": self.total_cost_of_ownership_eur,
        }


@dataclass(frozen=True)
class ReplayResult:
    """Full daily ledger and metrics for one causal replay."""

    ledger: pd.DataFrame
    metrics: ReplayMetrics
    history: ObservableHistory


ForecastProvider = Callable[[ForecastContext], Mapping[Pair, ForecastSnapshot]]
PolicyProvider = Callable[[PolicyContext], Mapping[Pair, int]]


def _normalise_daily_inputs(
    daily_targets: Sequence[DailyReplayInput] | Mapping[Any, Mapping[Pair, int]],
    return_tape: Optional[Mapping[Any, Mapping[Pair, int]]],
) -> list[DailyReplayInput]:
    """Accept typed daily records or a target mapping plus a separate return tape."""
    if isinstance(daily_targets, Mapping):
        returns = {
            _as_date(day): values for day, values in (return_tape or {}).items()
        }
        result = [
            DailyReplayInput(day, gross, returns.get(_as_date(day), {}))
            for day, gross in daily_targets.items()
        ]
    else:
        if return_tape:
            raise ValueError("return_tape is only used with mapping-form daily_targets")
        result = list(daily_targets)
    result.sort(key=lambda item: item.day)
    if not result:
        raise ValueError("daily_targets must contain at least one day")
    days = [item.day for item in result]
    if len(set(days)) != len(days):
        raise ValueError("daily_targets must contain one record per day")
    return result


def _normalise_cost_tape(
    cost_tape: Optional[Mapping[Any, Mapping[Pair, float]]],
) -> list[tuple[date, Mapping[Pair, float]]]:
    """Validate and sort dated cost observations without looking ahead."""
    if not cost_tape:
        return []
    observations: list[tuple[date, Mapping[Pair, float]]] = []
    for raw_day, costs in cost_tape.items():
        day = _as_date(raw_day)
        clean = {pair: _money(value, name=f"cost_tape[{pair!r}]") for pair, value in costs.items()}
        observations.append((day, MappingProxyType(clean)))
    observations.sort(key=lambda item: item[0])
    return observations


def _freeze_history(
    *,
    as_of: date,
    dates: Sequence[date],
    fulfilled: Mapping[Pair, list[int]],
    availability: Mapping[Pair, list[bool]],
) -> ObservableHistory:
    """Create a read-only history snapshot for callbacks."""
    return ObservableHistory(
        as_of=as_of,
        dates=tuple(dates),
        fulfilled_purchases=MappingProxyType({pair: tuple(values) for pair, values in fulfilled.items()}),
        availability=MappingProxyType({pair: tuple(values) for pair, values in availability.items()}),
    )


def _validate_order_decisions(
    decisions: Mapping[Pair, int],
    known_pairs: set[Pair],
    minimum_order_qty: int,
) -> dict[Pair, int]:
    """Validate callback output so physical stock and orders stay whole units."""
    if not isinstance(decisions, Mapping):
        raise TypeError("policy_provider must return a mapping of pair to whole-unit order quantity")
    unknown = set(decisions) - known_pairs
    if unknown:
        raise ValueError(f"policy_provider returned unknown pairs: {sorted(map(repr, unknown))}")
    result: dict[Pair, int] = {}
    for pair, raw_qty in decisions.items():
        qty = _whole_units(raw_qty, name=f"order_qty[{pair!r}]")
        if qty and qty < minimum_order_qty:
            raise ValueError(
                f"order_qty[{pair!r}]={qty} is below minimum_order_qty={minimum_order_qty}"
            )
        if qty:
            result[pair] = qty
    return result


def run_causal_replay(
    initial_state: Mapping[Pair, InitialPairState | int | None],
    daily_targets: Sequence[DailyReplayInput] | Mapping[Any, Mapping[Pair, int]],
    cost_tape: Optional[Mapping[Any, Mapping[Pair, float]]] = None,
    forecast_snapshot_provider: Optional[ForecastProvider] = None,
    policy_provider: Optional[PolicyProvider] = None,
    *,
    return_tape: Optional[Mapping[Any, Mapping[Pair, int]]] = None,
    activation_tape: Optional[Mapping[Pair, tuple[Any, int]]] = None,
    lead_time_days: int = 10,
    minimum_order_qty: int = 1,
    cost_assumptions: Optional[ReplayCostAssumptions] = None,
) -> ReplayResult:
    """Replay recorded gross purchases under a causal, whole-unit policy.

    ``daily_targets`` is the recorded gross-purchase target.  It is not
    demand observed by the forecast.  The forecast sees only fulfilled units
    and whether stock was available.  Returns are applied separately at the
    end of each day and never enter that history as demand.

    Args:
        initial_state: Pair opening stock.  ``None`` marks an unanchored pair.
        daily_targets: Typed daily records, or ``date -> pair -> units``.
        cost_tape: Dated pair costs.  A cost becomes visible on its date and is
            carried forward only after that date.
        forecast_snapshot_provider: Optional callback receiving causal history.
        policy_provider: Optional callback returning whole-unit pair orders.
        return_tape: Separate returns when mapping-form targets are used.
        activation_tape: Optional pair -> (activation date, opening stock).
            This activates a pair on the day after its first usable stock
            snapshot, so the snapshot is used once as starting inventory.
        lead_time_days: Calendar days from order placement to arrival.
        minimum_order_qty: Minimum positive order quantity enforced at runtime.
        cost_assumptions: Explicit scenario accounting assumptions.  No
            historical PO cost is inferred when this is omitted.

    Returns:
        A daily ledger, causal observable history, and scope-aware metrics.
    """
    if isinstance(lead_time_days, bool) or not isinstance(lead_time_days, Integral) or lead_time_days < 1:
        raise ValueError("lead_time_days must be a positive whole number")
    lead_time_days = int(lead_time_days)
    minimum_order_qty = _whole_units(minimum_order_qty, name="minimum_order_qty") or 0
    if minimum_order_qty < 1:
        raise ValueError("minimum_order_qty must be at least one unit")
    assumptions = cost_assumptions

    inputs = _normalise_daily_inputs(daily_targets, return_tape)
    cost_observations = _normalise_cost_tape(cost_tape)
    state: dict[Pair, Optional[int]] = {}
    for pair, raw_state in initial_state.items():
        if isinstance(raw_state, InitialPairState):
            state[pair] = raw_state.on_hand
        else:
            state[pair] = _whole_units(raw_state, name=f"initial_state[{pair!r}]", allow_none=True)

    target_pairs = set(state)
    for item in inputs:
        target_pairs.update(item.gross_purchases)
        target_pairs.update(item.returns)
    for _, day_costs in cost_observations:
        target_pairs.update(day_costs)
    known_pairs = {pair for pair, on_hand in state.items() if on_hand is not None}

    activations: dict[Pair, tuple[date, int]] = {}
    for pair, raw_activation in (activation_tape or {}).items():
        if pair not in state:
            state[pair] = None
            target_pairs.add(pair)
        if not isinstance(raw_activation, (tuple, list)) or len(raw_activation) != 2:
            raise TypeError("activation_tape values must be (date, whole-unit opening stock) pairs")
        activation_day = _as_date(raw_activation[0])
        opening_qty = _whole_units(raw_activation[1], name=f"activation_tape[{pair!r}][1]")
        activations[pair] = (activation_day, opening_qty)

    # No state means no causal stock anchor; retain the row but exclude it.
    for pair in target_pairs - set(state):
        state[pair] = None

    current_costs: dict[Pair, float] = {}
    pending: dict[date, dict[Pair, int]] = {}
    fulfilled_history: dict[Pair, list[int]] = {pair: [] for pair in sorted(target_pairs, key=repr)}
    availability_history: dict[Pair, list[bool]] = {pair: [] for pair in sorted(target_pairs, key=repr)}
    observed_dates: list[date] = []
    rows: list[dict[str, Any]] = []
    order_events = 0
    order_units = 0
    valued_inventory_sum = 0.0
    valued_pair_days = 0
    inventory_pair_days = 0
    eligible_pair_days = 0
    available_pair_days = 0
    target_units = 0
    fulfilled_units = 0
    cost_index = 0

    for item in inputs:
        day = item.day
        for pair, (activation_day, opening_qty) in activations.items():
            if activation_day <= day and state.get(pair) is None:
                state[pair] = opening_qty
                known_pairs.add(pair)
        while cost_index < len(cost_observations) and cost_observations[cost_index][0] <= day:
            _, day_costs = cost_observations[cost_index]
            current_costs.update(day_costs)
            cost_index += 1

        arrivals = pending.pop(day, {})
        day_rows: dict[Pair, dict[str, Any]] = {}
        for pair in sorted(target_pairs, key=repr):
            target = item.gross_purchases.get(pair, 0)
            returns = item.returns.get(pair, 0)
            on_hand = state[pair]
            if on_hand is None:
                day_rows[pair] = {
                    "date": day,
                    "pair": pair,
                    "eligible": False,
                    "exclusion_reason": "unknown_initial_stock",
                    "opening_on_hand_units": None,
                    "arrivals_units": 0,
                    "recorded_gross_purchases_units": target,
                    "fulfilled_purchases_units": 0,
                    "unfulfilled_purchases_units": target,
                    "returns_units": returns,
                    "closing_on_hand_units": None,
                    "on_order_units": 0,
                    "inventory_position_units": None,
                    "order_qty_units": 0,
                    "policy_unavailable_reason": "unknown_initial_stock",
                    "mass_balance_residual_units": None,
                    "available_for_sale": None,
                    "unit_cost_eur": current_costs.get(pair),
                    "inventory_value_eur": None,
                    "activation_date": activations.get(pair, (None, None))[0],
                }
                fulfilled_history[pair].append(0)
                availability_history[pair].append(False)
                continue

            arrival_qty = arrivals.get(pair, 0)
            opening = on_hand
            available = (opening + arrival_qty) > 0
            shelf_before_demand = opening + arrival_qty
            from src.simulation.movements import stock_movements
            fulfilled, closing, fully_available = stock_movements(opening, arrival_qty, target, returns)
            fulfilled, closing = int(fulfilled), int(closing)
            unfulfilled = target - fulfilled
            state[pair] = closing
            eligible_pair_days += 1
            inventory_pair_days += 1
            available_pair_days += int(available)
            target_units += target
            fulfilled_units += fulfilled
            fulfilled_history[pair].append(fulfilled)
            availability_history[pair].append(bool(fully_available))
            unit_cost = current_costs.get(pair)
            inventory_value = float(closing * unit_cost) if unit_cost is not None else None
            if inventory_value is not None:
                valued_pair_days += 1
                valued_inventory_sum += inventory_value
            day_rows[pair] = {
                "date": day,
                "pair": pair,
                "eligible": True,
                "exclusion_reason": None,
                "opening_on_hand_units": opening,
                "arrivals_units": arrival_qty,
                "recorded_gross_purchases_units": target,
                "fulfilled_purchases_units": fulfilled,
                "unfulfilled_purchases_units": unfulfilled,
                "returns_units": returns,
                "closing_on_hand_units": closing,
                "on_order_units": sum(pending_day.get(pair, 0) for pending_day in pending.values()),
                "inventory_position_units": closing + sum(pending_day.get(pair, 0) for pending_day in pending.values()),
                "order_qty_units": 0,
                "policy_unavailable_reason": None,
                "mass_balance_residual_units": int(opening + arrival_qty - fulfilled + returns - closing),
                "available_for_sale": available,
                "unit_cost_eur": unit_cost,
                "inventory_value_eur": inventory_value,
                "activation_date": activations.get(pair, (None, None))[0],
            }

        observed_dates.append(day)
        history = _freeze_history(
            as_of=day,
            dates=observed_dates,
            fulfilled=fulfilled_history,
            availability=availability_history,
        )
        forecast_context = ForecastContext(as_of=day, history=history)
        raw_forecasts = forecast_snapshot_provider(forecast_context) if forecast_snapshot_provider else {}
        if not isinstance(raw_forecasts, Mapping):
            raise TypeError("forecast_snapshot_provider must return a mapping")
        forecasts = dict(raw_forecasts)
        active_pairs = {pair for pair, value in state.items() if value is not None}
        unknown_forecasts = set(forecasts) - active_pairs
        if unknown_forecasts:
            raise ValueError(f"forecast_snapshot_provider returned unknown pairs: {sorted(map(repr, unknown_forecasts))}")
        closing = {pair: int(state[pair]) for pair in active_pairs}
        on_order = {
            pair: sum(pending_day.get(pair, 0) for pending_day in pending.values())
            for pair in active_pairs
        }
        inventory_position = {pair: closing[pair] + on_order[pair] for pair in active_pairs}
        policy_context = PolicyContext(
            as_of=day,
            closing_on_hand=MappingProxyType(dict(closing)),
            on_order=MappingProxyType(dict(on_order)),
            inventory_position=MappingProxyType(dict(inventory_position)),
            costs=MappingProxyType({pair: current_costs.get(pair) for pair in active_pairs}),
            forecasts=MappingProxyType(dict(forecasts)),
            history=history,
        )
        raw_decisions = policy_provider(policy_context) if policy_provider else {}
        decisions = _validate_order_decisions(raw_decisions, active_pairs, minimum_order_qty)
        # A policy cannot safely value a new order without a cost known by the
        # decision date.  Keep the decision visible and suppress the physical
        # order until a causal cost observation arrives.
        unavailable_pairs = [pair for pair in decisions if pair not in current_costs]
        for pair in unavailable_pairs:
            day_rows[pair]["policy_unavailable_reason"] = "missing_cost_at_decision"
            del decisions[pair]
        # Record a reason for every eligible pair-day, including days on
        # which the policy correctly chose not to order.  This makes a quiet
        # zero distinguishable from an unavailable recommendation.
        for pair in active_pairs:
            if pair not in day_rows:
                continue
            if day_rows[pair]["policy_unavailable_reason"] is not None:
                continue
            if pair not in current_costs:
                day_rows[pair]["policy_unavailable_reason"] = "missing_cost_at_decision"
            elif pair not in forecasts:
                day_rows[pair]["policy_unavailable_reason"] = "forecast_unavailable"
            elif pair not in decisions:
                day_rows[pair]["policy_unavailable_reason"] = "no_order_policy_rule"
        arrival_day = day + timedelta(days=lead_time_days)
        if arrival_day not in pending:
            pending[arrival_day] = {}
        for pair, qty in decisions.items():
            pending[arrival_day][pair] = pending[arrival_day].get(pair, 0) + qty
            order_events += 1
            order_units += qty
            day_rows[pair]["order_qty_units"] = qty
            day_rows[pair]["on_order_units"] = sum(pending_day.get(pair, 0) for pending_day in pending.values())
            day_rows[pair]["inventory_position_units"] = state[pair] + day_rows[pair]["on_order_units"]

        rows.extend(day_rows[pair] for pair in sorted(day_rows, key=repr))

    ledger = pd.DataFrame(rows)
    if not ledger.empty:
        ledger["date"] = pd.to_datetime(ledger["date"])
        for column in (
            "opening_on_hand_units", "arrivals_units", "recorded_gross_purchases_units",
            "fulfilled_purchases_units", "unfulfilled_purchases_units", "returns_units",
            "closing_on_hand_units", "on_order_units", "inventory_position_units", "order_qty_units",
        ):
            # Nullable integer keeps the unknown-stock rows honest.
            ledger[column] = ledger[column].astype("Int64")

    total_unfulfilled = target_units - fulfilled_units
    ending_on_hand_units = sum(on_hand or 0 for on_hand in state.values())
    coverage = float(fulfilled_units / target_units) if target_units else None
    availability_rate = float(available_pair_days / eligible_pair_days) if eligible_pair_days else None
    average_value = float(valued_inventory_sum / valued_pair_days) if valued_pair_days else None
    if not ledger.empty:
        daily_values = ledger.loc[ledger["eligible"] == True].groupby("date")["inventory_value_eur"].sum(min_count=1)
        average_daily_value = float(daily_values.mean()) if not daily_values.empty else None
    else:
        average_daily_value = None
    inventory_cost_coverage = float(valued_pair_days / inventory_pair_days) if inventory_pair_days else 0.0
    holding_cost = None
    ordering_cost = None
    if assumptions is not None:
        if assumptions.annual_holding_rate is not None:
            holding_cost = float(
                valued_inventory_sum * assumptions.annual_holding_rate / assumptions.annual_days
            )
        if assumptions.fixed_order_cost_eur is not None or assumptions.line_order_cost_eur is not None:
            fixed = assumptions.fixed_order_cost_eur or 0.0
            line = assumptions.line_order_cost_eur or 0.0
            # The primitive knows order lines but not store identities.  The
            # report layer applies the fixed store-day batch charge.  Keep the
            # line component here only when explicitly requested.
            ordering_cost = float(order_events * line) if assumptions.line_order_cost_eur is not None else None
        if holding_cost is not None and ordering_cost is not None:
            total_tco = holding_cost + ordering_cost
        else:
            total_tco = None
    else:
        total_tco = None

    metrics = ReplayMetrics(
        total_target_units=target_units,
        total_fulfilled_units=fulfilled_units,
        total_unfulfilled_units=total_unfulfilled,
        observed_purchase_coverage=coverage,
        eligible_pair_days=eligible_pair_days,
        available_pair_days=available_pair_days,
        availability_rate=availability_rate,
        ending_on_hand_units=ending_on_hand_units,
        total_order_units=order_units,
        total_order_events=order_events,
        average_inventory_value_eur=average_value,
        average_daily_inventory_value_eur=average_daily_value,
        valued_pair_days=valued_pair_days,
        inventory_pair_days=inventory_pair_days,
        inventory_cost_coverage=inventory_cost_coverage,
        holding_cost_eur=holding_cost,
        ordering_cost_eur=ordering_cost,
        total_cost_of_ownership_eur=total_tco,
    )
    final_history = _freeze_history(
        as_of=inputs[-1].day,
        dates=observed_dates,
        fulfilled=fulfilled_history,
        availability=availability_history,
    )
    return ReplayResult(ledger=ledger, metrics=metrics, history=final_history)


__all__ = [
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
