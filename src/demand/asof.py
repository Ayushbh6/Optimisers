"""Historical daily demand estimates using the same learner as replay."""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.demand.config import DemandConfig, DEFAULT_DEMAND_CONFIG
from src.demand.state import DemandState
from src.data.metadata import resolve_metadata, category_keys


def estimate_demand_asof(daily_onhand: pd.DataFrame, hierarchy: pd.DataFrame, *, config: DemandConfig = DEFAULT_DEMAND_CONFIG) -> pd.DataFrame:
    """Estimate using prior-day exposure and explicitly assessed stock availability."""
    result = daily_onhand.sort_values(['date', 'Product No', 'Store'], kind='stable').reset_index(drop=True).copy()
    pairs = pd.MultiIndex.from_frame(result[['Product No', 'Store']]).unique()
    state = DemandState(pairs, config.min_in_stock_days_sku_store)
    n = len(result)
    estimates = np.zeros(n); methods = np.full(n, '', object); availability = np.full(n, '', object)
    donors = np.zeros(n, np.int64); assumed = np.zeros(n, np.int64); exposure = np.zeros(n, bool)
    for day, positions in result.groupby('date', sort=True).indices.items():
        rows = result.iloc[positions]
        index = pairs.get_indexer(pd.MultiIndex.from_frame(rows[['Product No', 'Store']]))
        known = rows['stock_known'].to_numpy(bool)
        qty = pd.to_numeric(rows['qty_onhand'], errors='coerce').to_numpy(dtype=float, na_value=np.nan)
        returns = rows['returned_qty'].to_numpy(float)
        discrepant = np.zeros(len(rows), bool)
        for column, negative in [('stock_discrepancy_unresolved', False), ('unexplained_shortfall', False), ('reconciliation_adjustment', False), ('raw_qty_onhand', True)]:
            if column in rows:
                values = rows[column].fillna(0).to_numpy(float)
                discrepant |= values < 0 if negative else np.abs(values) > 1e-9
        available = known & (qty - returns > 0) & ~discrepant
        full_purchases = np.zeros(len(pairs)); full_known = np.zeros(len(pairs), bool); full_available = np.zeros(len(pairs), bool)
        full_assumed = np.zeros(len(pairs), bool)
        full_purchases[index] = rows['gross_qty_sold']
        full_known[index] = known; full_available[index] = available
        bridged = rows.get('source', pd.Series('', index=rows.index)).eq('bridged_assumed').to_numpy()
        full_assumed[index] = bridged & available
        categories = category_keys(resolve_metadata(hierarchy, day, pairs))
        est, method, donor_n, assumed_n = state.step(full_purchases, full_known, full_available, categories, estimated_exposure=full_assumed)
        estimates[positions] = est[index]; methods[positions] = method[index]
        donors[positions] = donor_n[index]; assumed[positions] = assumed_n[index]
        exposure[positions] = bridged & available
        availability[positions] = np.where(~known, 'unknown_stock', np.where(discrepant, 'partial_or_discrepant', np.where(available, 'available', 'empty_or_depleted')))
    result['estimated_demand'] = estimates
    result['availability_assessment'] = availability
    result['estimate_fallback'] = methods
    result['information_cutoff'] = pd.to_datetime(result['date'])
    result['rate_information_cutoff'] = pd.to_datetime(result['date']) - pd.Timedelta(days=1)
    result['donor_exposure_source'] = np.where(availability == 'available', np.where(exposure, 'estimated_bridge', 'observed_snapshot_or_flow'), 'none')
    result['estimated_donor_exposure_days'] = exposure.astype(int)
    result['rate_donor_days'] = donors; result['rate_estimated_donor_days'] = assumed
    result['demand_definition'] = 'estimated demand; recorded purchases plus causal stockout estimate'
    return result
