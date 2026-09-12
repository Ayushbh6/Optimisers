"""Full-data recorded-purchase controller and isolated shop learning state."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import numpy as np
import pandas as pd
from src.run_contract import RunConfig
from src.data.metadata import resolve_metadata, category_keys
from src.demand.state import DemandState
from src.forecast.state import ForecastState
from src.policy.config import PolicyConfig
from src.policy.asof import build_asof_policy_snapshot


from src.simulation.movements import stock_movements


class ShopForecaster:
    """Receives purchases it fulfilled and shelf evidence, never purchase targets."""

    def __init__(self, pairs: pd.MultiIndex, config: RunConfig) -> None:
        self.demand = DemandState(pairs, config.minimum_exposure_days)
        self.forecast = ForecastState(pairs, method=config.forecast_method, alpha=config.alpha, beta=config.beta, prior=config.laplace_prior)

    def observe(self, day: pd.Timestamp, fulfilled: np.ndarray, known: np.ndarray, available: np.ndarray, metadata: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Infer missing demand from the shop's own past available-day rates."""
        estimate, method, donor_n, assumed_n = self.demand.step(fulfilled, known, available, category_keys(metadata))
        self.forecast.add(day, estimate, known)
        return estimate, method, donor_n, assumed_n


@dataclass
class ReplayInputs:
    """Controller-owned purchase tape, unavailable to the shop's history contract."""
    pairs: pd.MultiIndex
    dates: pd.DatetimeIndex
    purchases: np.ndarray
    returns: np.ndarray
    costs: np.ndarray
    activation: np.ndarray
    opening: np.ndarray
    metadata: list
    template: ShopForecaster
    initial_metadata: pd.DataFrame
    first_seen: np.ndarray


def prepare_replay(daily: pd.DataFrame, demand: pd.DataFrame, hierarchy: pd.DataFrame, config: RunConfig) -> ReplayInputs:
    """Prepare facts once and train the common initial state before replay starts."""
    pairs = pd.MultiIndex.from_frame(daily[['Product No', 'Store']]).unique().sort_values()
    dates = pd.date_range(config.replay_start, config.observation_end)
    shape = (len(dates), len(pairs))
    purchases = np.zeros(shape, np.int64); returns = purchases.copy(); costs = np.full(shape, np.nan)
    activation = np.full(len(pairs), len(dates), int); opening = np.zeros(len(pairs), np.int64)
    history = daily.loc[pd.to_datetime(daily.date) <= pd.Timestamp(config.initial_learning_end), ['Product No', 'Store', 'date', 'stock_known', 'qty_onhand', 'unit_cost']]
    initial = history[history.stock_known].sort_values('date').drop_duplicates(['Product No', 'Store'], keep='last')
    idx = pairs.get_indexer(pd.MultiIndex.from_frame(initial[['Product No', 'Store']]))
    initial_values = initial.qty_onhand.to_numpy(float)
    if np.any((initial_values < 0) | (initial_values != np.floor(initial_values))):
        raise ValueError("Starting stock must contain whole units")
    activation[idx] = 0; opening[idx] = initial_values.astype(np.int64)
    for i, day in enumerate(dates):
        rows = daily[daily.date == day]
        idx = pairs.get_indexer(pd.MultiIndex.from_frame(rows[['Product No', 'Store']]))
        for column in ('gross_qty_sold', 'returned_qty', 'qty_onhand'):
            values = rows[column].dropna().to_numpy(float)
            if np.any((values < 0) | (values != np.floor(values))):
                raise ValueError(f'{column} must contain whole physical units')
        purchases[i, idx] = rows.gross_qty_sold.to_numpy(np.int64)
        returns[i, idx] = rows.returned_qty.to_numpy(np.int64)
        costs[i, idx] = rows.unit_cost.to_numpy(float)
        anchor = rows.stock_known.to_numpy(bool) & (activation[idx] == len(dates))
        activation[idx[anchor]] = i + 1
        opening[idx[anchor]] = rows.loc[anchor, 'qty_onhand'].to_numpy(np.int64)
    # A cost is an observed fact independent of subsequent historical stock.
    initial_cost = np.full(len(pairs), np.nan)
    cost_rows = history[history.unit_cost.notna() & (history.unit_cost > 0)].sort_values('date').drop_duplicates(['Product No', 'Store'], keep='last')
    idx = pairs.get_indexer(pd.MultiIndex.from_frame(cost_rows[['Product No', 'Store']]))
    initial_cost[idx] = cost_rows.unit_cost
    costs = pd.DataFrame(np.vstack([initial_cost, costs])).ffill().to_numpy()[1:]
    template = ShopForecaster(pairs, config)
    initial_demand = demand.loc[demand.date <= pd.Timestamp(config.initial_learning_end), ['Product No', 'Store', 'date', 'gross_qty_sold', 'stock_known', 'availability_assessment', 'donor_exposure_source', 'estimated_demand']]
    for day, rows in initial_demand.groupby('date', sort=True):
        idx = pairs.get_indexer(pd.MultiIndex.from_frame(rows[['Product No', 'Store']]))
        gross = np.zeros(len(pairs)); known = np.zeros(len(pairs), bool); available = known.copy(); assumed = known.copy()
        gross[idx] = rows.gross_qty_sold; known[idx] = rows.stock_known; available[idx] = rows.availability_assessment.eq('available')
        assumed[idx] = rows.donor_exposure_source.eq('estimated_bridge')
        metadata = resolve_metadata(hierarchy, day, pairs)
        template.demand.step(gross, known, available, category_keys(metadata), estimated_exposure=assumed)
        estimates = np.zeros(len(pairs)); present = np.zeros(len(pairs), bool)
        estimates[idx] = rows.estimated_demand; present[idx] = True
        template.forecast.add(day, estimates, present)
    metadata = [resolve_metadata(hierarchy, day, pairs) for day in dates]
    initial_metadata = resolve_metadata(hierarchy, config.initial_learning_end, pairs)
    first_seen = daily.groupby(["Product No", "Store"]).date.min().reindex(pairs).to_numpy()
    return ReplayInputs(pairs, dates, purchases, returns, costs, activation, opening, metadata, template, initial_metadata, first_seen)


def replay_prepared(inputs: ReplayInputs, config: RunConfig, policy_config: PolicyConfig, *, traces: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Run a fresh shop; controller alone owns target demand and activation facts."""
    shop = deepcopy(inputs.template)
    n = len(inputs.pairs)
    stock = np.zeros(n, np.int64); on_order = stock.copy()
    pending = np.zeros((len(inputs.dates) + config.lead_time_days, n), np.int64)
    ledgers, forecasts, policies = [], [], []
    initial_forecast = shop.forecast.snapshot(inputs.initial_metadata.loc[inputs.activation == 0], pd.Timestamp(config.initial_learning_end))
    initial_forecast['forecast_status'] = 'available'
    if traces:
        forecasts.append(initial_forecast)
    products = inputs.pairs.get_level_values(0).to_numpy(); stores = inputs.pairs.get_level_values(1).to_numpy()
    for i, day in enumerate(inputs.dates):
        active = inputs.activation <= i
        starting = inputs.activation == i
        stock[starting] = inputs.opening[starting]
        opening = stock.copy(); arrivals = pending[i].copy(); on_order -= arrivals
        fulfilled, closing, available = stock_movements(opening, arrivals, inputs.purchases[i], inputs.returns[i])
        fulfilled[~active] = 0; closing[~active] = 0; available &= active
        estimate, fallback, donors, assumed = shop.observe(day, fulfilled, active, available, inputs.metadata[i])
        forecast = shop.forecast.snapshot(inputs.metadata[i].loc[active], day)
        forecast_idx = inputs.pairs.get_indexer(pd.MultiIndex.from_frame(forecast[['Product No', 'Store']]))
        forecast = forecast[active[forecast_idx]].copy(); forecast_idx = forecast_idx[active[forecast_idx]]
        costs = pd.DataFrame({'Product No': products, 'Store': stores, 'unit_cost_as_of': inputs.costs[i]})
        policy = build_asof_policy_snapshot(forecast, costs, policy_config)
        position = closing + on_order
        quantity = np.zeros(n, np.int64)
        reasons = np.full(n, 'forecast_unavailable', object)
        reasons[~active] = 'unknown_starting_stock'
        if not policy.empty:
            idx = inputs.pairs.get_indexer(pd.MultiIndex.from_frame(policy[['Product No', 'Store']]))
            usable = policy.policy_status.eq('available').to_numpy()
            stocked = policy.is_stocked.to_numpy(bool)
            trigger = usable & stocked & (position[idx] <= policy.reorder_point_s.to_numpy(float))
            gaps = policy.order_up_to_S.to_numpy(float) - position[idx]
            quantity[idx[trigger]] = np.maximum(config.min_order_quantity, np.ceil(gaps[trigger])).astype(np.int64)
            reasons[idx] = np.where(~usable, 'missing_cost_at_decision', np.where(~stocked, 'below_stocking_threshold', np.where(trigger, 'order_placed', 'above_reorder_point')))
        pending[i + config.lead_time_days] += quantity; on_order += quantity; stock = closing
        ledger = pd.DataFrame({'date': day, 'Product No': products, 'Store': stores,
            'Product Division': inputs.metadata[i]['Product Division'].to_numpy(), 'eligible': active,
            'opening_on_hand_units': np.where(active, opening, np.nan), 'arrivals_units': arrivals,
            'recorded_gross_purchases_units': inputs.purchases[i], 'fulfilled_purchases_units': fulfilled,
            'unfulfilled_purchases_units': inputs.purchases[i] - fulfilled, 'returns_units': inputs.returns[i],
            'closing_on_hand_units': np.where(active, closing, np.nan), 'on_order_units': on_order,
            'decision_inventory_position_units': np.where(active, position, np.nan), 'inventory_position_units': np.where(active, closing + on_order, np.nan), 'order_qty_units': quantity,
            'policy_unavailable_reason': reasons, 'mass_balance_residual_units': np.where(active, opening + arrivals + inputs.returns[i] - fulfilled - closing, np.nan),
            'available_for_sale': available, 'unit_cost_eur': inputs.costs[i],
            'inventory_value_eur': np.where(active, closing * inputs.costs[i], np.nan),
            'estimated_demand': np.where(active, estimate, np.nan), 'estimate_fallback': fallback,
            'availability_assessment': np.where(~active, 'unknown_stock', np.where(available, 'available', 'empty_or_depleted')),
            'rate_information_cutoff': day - pd.Timedelta(days=1), 'rate_donor_days': donors,
            'rate_estimated_donor_days': assumed, 'order_arrival_date': day + pd.Timedelta(days=config.lead_time_days)})
        ledger = ledger[inputs.first_seen <= day.to_datetime64()].copy()
        ledgers.append(ledger)
        if traces:
            audit_forecast = pd.DataFrame({'Product No': products[active], 'Store': stores[active]}).merge(forecast, on=['Product No', 'Store'], how='left', validate='one_to_one')
            audit_forecast['forecast_status'] = np.where(audit_forecast.daily_expected_demand.notna(), 'available', 'unavailable_history_or_metadata')
            audit_forecast['information_cutoff'] = day
            audit_forecast['forecast_start_date'] = day + pd.Timedelta(days=1)
            forecasts.append(audit_forecast)
            trace = ledger.loc[ledger.eligible, ['date', 'Product No', 'Store', 'policy_unavailable_reason', 'order_qty_units', 'inventory_position_units']].rename(columns={'date': 'as_of'})
            trace = trace.merge(policy, on=['Product No', 'Store'], how='left', validate='one_to_one')
            trace['no_order_reason'] = trace.policy_unavailable_reason
            trace['forecast_available'] = trace.daily_expected_demand.notna()
            trace['policy_status'] = trace.policy_status.fillna('unavailable_forecast')
            policies.append(trace)
    ledger = pd.concat(ledgers, ignore_index=True)
    for column in [c for c in ledger if c.endswith("_units") and c not in ("estimated_demand",)]:
        ledger[column] = ledger[column].astype("Int64")
    eligible = ledger[ledger.eligible]
    target = int(eligible.recorded_gross_purchases_units.sum()); fulfilled = int(eligible.fulfilled_purchases_units.sum())
    metrics = {'total_target_units': target, 'total_fulfilled_units': fulfilled, 'total_unfulfilled_units': target - fulfilled,
        'observed_purchase_coverage': fulfilled / target if target else None, 'ending_on_hand_units': int(stock.sum()),
        'average_daily_inventory_value_eur': eligible.groupby('date').inventory_value_eur.sum(min_count=1).mean()}
    return ledger, pd.concat(forecasts, ignore_index=True) if traces else pd.DataFrame(), pd.concat(policies, ignore_index=True) if traces else pd.DataFrame(), metrics
