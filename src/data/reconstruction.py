"""Causal daily stock reconstruction with a separate historical reference view."""

from __future__ import annotations

from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from src.data.config import DataConfig, DEFAULT_CONFIG
from src.data.loader import aggregate_daily_sales


def expand_inventory_intervals(inv_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Expand retrospective intervals for accounting only.

    Downstream forecasting and policy code must use the causal fields emitted by
    :func:`reconstruct_daily_onhand`, never this retrospective view.
    """
    durations = (inv_df["End Date_parsed"] - inv_df["Start Date"]).dt.days + 1
    if (durations < 1).any():
        raise ValueError("Inventory has an interval ending before it starts")
    counts = durations.to_numpy(dtype=int)
    source_rows = np.repeat(np.arange(len(inv_df)), counts)
    offsets = np.arange(counts.sum()) - np.repeat(np.r_[0, np.cumsum(counts)[:-1]], counts)
    raw_qty = inv_df["Qty on hand"].to_numpy(float)[source_rows]
    result = pd.DataFrame({
        "Product No": inv_df["Product No"].to_numpy()[source_rows],
        "Store": inv_df["Store"].to_numpy()[source_rows],
        "date": inv_df["Start Date"].to_numpy()[source_rows] + offsets.astype("timedelta64[D]"),
        "reference_raw_qty_onhand": raw_qty,
        "reference_qty_onhand": np.maximum(raw_qty, 0.0),
        "reference_unit_cost": inv_df["Stock Unit Cost Price"].to_numpy(float)[source_rows],
        "reference_unit_selling_price": inv_df["Stock Unit Selling Price"].to_numpy(float)[source_rows],
        "reference_stock_status": inv_df["Stock Status"].to_numpy()[source_rows],
        "snapshot_start_date": inv_df["Start Date"].to_numpy()[source_rows],
    })
    for column, output in (("Cost of Stocks", "reference_raw_cost_of_stocks"), ("Stocks Selling Amount", "reference_raw_stocks_selling_amount")):
        if column in inv_df:
            result[output] = inv_df[column].to_numpy()[source_rows]
    result = result.sort_values(["Product No", "Store", "date", "snapshot_start_date"]).drop_duplicates(
        ["Product No", "Store", "date"], keep="last"
    ).drop(columns="snapshot_start_date")
    return result, {
        "raw_intervals_count": len(inv_df),
        "expanded_reference_rows": len(result),
        "raw_negative_records": int((inv_df["Qty on hand"] < 0).sum()),
        "min_raw_qty": float(inv_df["Qty on hand"].min()),
    }


def _daily_grid(inv_df: pd.DataFrame, sales: pd.DataFrame, config: DataConfig) -> pd.DataFrame:
    starts = inv_df.groupby(["Product No", "Store"], as_index=False)["Start Date"].min().rename(columns={"Start Date": "inventory_start"})
    sale_starts = sales.groupby(["Product No", "Store"], as_index=False)["date"].min().rename(columns={"date": "sales_start"})
    pairs = starts.merge(sale_starts, on=["Product No", "Store"], how="outer")
    pairs["start"] = pairs[["inventory_start", "sales_start"]].min(axis=1)
    pairs = pairs[pairs["start"].notna()].sort_values(["Product No", "Store"]).reset_index(drop=True)
    horizon = pd.Timestamp(config.observation_end_date)
    counts = (horizon - pairs["start"]).dt.days.to_numpy(int) + 1
    index = np.repeat(np.arange(len(pairs)), counts)
    offsets = np.arange(counts.sum()) - np.repeat(np.r_[0, np.cumsum(counts)[:-1]], counts)
    return pd.DataFrame({
        "Product No": pairs["Product No"].to_numpy()[index],
        "Store": pairs["Store"].to_numpy()[index],
        "date": pairs["start"].to_numpy()[index] + offsets.astype("timedelta64[D]"),
    })


def reconstruct_daily_onhand(
    inv_df: pd.DataFrame, sales_df: pd.DataFrame, config: DataConfig = DEFAULT_CONFIG
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Build daily causal stock estimates and retrospective reference coverage.

    Interval end dates are used only in the separate historical reference view.
    The causal state is updated from snapshots at their start date and from
    same-day purchases/returns; a later snapshot or interval ending never
    changes an earlier causal row.
    """
    reference, stats = expand_inventory_intervals(inv_df)
    sales = aggregate_daily_sales(sales_df)
    grid = _daily_grid(inv_df, sales, config)
    snap_cols = ["Product No", "Store", "Start Date", "Qty on hand", "Stock Unit Cost Price", "Stock Unit Selling Price", "Stock Status"]
    snapshots = inv_df[snap_cols].sort_values(["Product No", "Store", "Start Date"]).drop_duplicates(
        ["Product No", "Store", "Start Date"], keep="last"
    ).rename(columns={
        "Start Date": "date", "Qty on hand": "snapshot_raw_qty_onhand", "Stock Unit Cost Price": "snapshot_unit_cost",
        "Stock Unit Selling Price": "snapshot_unit_selling_price", "Stock Status": "snapshot_stock_status",
    })
    data = grid.merge(sales, on=["Product No", "Store", "date"], how="left")
    data = data.merge(snapshots, on=["Product No", "Store", "date"], how="left")
    data = data.merge(reference, on=["Product No", "Store", "date"], how="left")
    for column in ("raw_qty_sold", "gross_qty_sold", "returned_qty", "net_qty_sold"):
        data[column] = data[column].fillna(0.0)
    data = data.sort_values(["Product No", "Store", "date"]).reset_index(drop=True)

    causal_qty = np.full(len(data), np.nan)
    raw_qty = np.full(len(data), np.nan)
    source = np.full(len(data), "unknown_before_anchor", dtype=object)
    adjustment = np.full(len(data), np.nan)
    shortfall = np.zeros(len(data), dtype=float)
    costs = np.full(len(data), np.nan)
    prices = np.full(len(data), np.nan)
    statuses = np.full(len(data), None, dtype=object)
    unresolved = np.zeros(len(data), dtype=bool)
    cost_source = np.full(len(data), "unavailable", dtype=object)

    # Keep the state machine sequential, but read its inputs as arrays.  A
    # DataFrame ``iloc`` call for every pair-day made the full 14M-row build
    # needlessly expensive.
    dates = data["date"].to_numpy()
    gross = data["gross_qty_sold"].to_numpy(dtype=float)
    returned = data["returned_qty"].to_numpy(dtype=float)
    snapshot_qty = data["snapshot_raw_qty_onhand"].to_numpy(dtype=float)
    snapshot_cost = data["snapshot_unit_cost"].to_numpy(dtype=float)
    snapshot_price = data["snapshot_unit_selling_price"].to_numpy(dtype=float)
    snapshot_status = data["snapshot_stock_status"].to_numpy(dtype=object)

    for _, positions in data.groupby(["Product No", "Store"], sort=False).indices.items():
        discrepancy_open = False
        previous: float | None = None
        previous_cost: float | None = None
        previous_price: float | None = None
        previous_status: object | None = None
        for pos in positions:
            is_snapshot = np.isfinite(snapshot_qty[pos])
            if np.isfinite(snapshot_cost[pos]) and snapshot_cost[pos] > 0:
                previous_cost = snapshot_cost[pos]
            if previous_cost is not None:
                costs[pos] = previous_cost
                cost_source[pos] = "snapshot_observed" if np.isfinite(snapshot_cost[pos]) and snapshot_cost[pos] > 0 else "pair_prior_assumed"
            if np.isfinite(snapshot_price[pos]):
                previous_price = snapshot_price[pos]
            if is_snapshot:
                discrepancy_open = False
                observed_raw = snapshot_qty[pos]
                observed = max(0.0, observed_raw)
                raw_qty[pos] = observed_raw
                if previous is not None:
                    shortfall[pos] = max(0.0, gross[pos] - previous)
                    # Snapshot quantities are closing stock.  Purchases
                    # consume opening stock first; returns arrive at day end.
                    expected = max(0.0, previous - gross[pos]) + returned[pos]
                    adjustment[pos] = observed - expected
                causal_qty[pos] = observed
                source[pos] = "snapshot_observed"
                previous = observed
                raw_cost = snapshot_cost[pos]
                if np.isfinite(raw_cost) and raw_cost > 0:
                    previous_cost = raw_cost
                    costs[pos] = raw_cost
                    cost_source[pos] = "snapshot_observed"
                if np.isfinite(snapshot_price[pos]):
                    previous_price = snapshot_price[pos]
                previous_status = snapshot_status[pos]
            elif previous is not None:
                demand = gross[pos]
                # Returns are a day-end movement.  They cannot make a
                # purchase earlier that same day fulfillable.
                shortfall[pos] = max(0.0, demand - previous)
                discrepancy_open |= shortfall[pos] > 0
                previous = max(0.0, previous - demand) + returned[pos]
                causal_qty[pos] = previous
                source[pos] = "bridged_assumed"
                if previous_cost is not None:
                    costs[pos] = previous_cost
                    cost_source[pos] = "pair_prior_assumed"
            unresolved[pos] = discrepancy_open
            if np.isnan(costs[pos]) and is_snapshot and previous_cost is not None:
                costs[pos] = previous_cost
            if previous_price is not None:
                prices[pos] = previous_price
            if previous_status is not None:
                statuses[pos] = previous_status

    data["stock_discrepancy_unresolved"] = unresolved
    data["qty_onhand"] = causal_qty
    data["raw_qty_onhand"] = raw_qty
    data["source"] = source
    data["stock_known"] = data["qty_onhand"].notna()
    data["reconciliation_adjustment"] = adjustment
    data["unexplained_shortfall"] = shortfall
    data["unit_cost"] = costs
    data["unit_selling_price"] = prices
    data["stock_status"] = statuses
    data["cost_source"] = cost_source
    data["valuation_eligible"] = data["stock_known"] & data["unit_cost"].notna() & (data["unit_cost"] > 0)
    wanted = list(config.daily_onhand_columns) + [
        "stock_discrepancy_unresolved", "raw_qty_sold", "gross_qty_sold", "returned_qty", "net_qty_sold", "reference_raw_qty_onhand", "reference_qty_onhand",
        "reference_unit_cost", "reference_unit_selling_price", "reference_stock_status", "cost_source", "valuation_eligible",
    ]
    wanted += [c for c in ("gross_sales_amount", "total_cogs", "transaction_count", "reference_raw_cost_of_stocks", "reference_raw_stocks_selling_amount") if c in data]
    result = data[[column for column in wanted if column in data.columns]].copy()
    stats.update({
        "total_daily_rows": len(result),
        "known_stock_rows": int(result["stock_known"].sum()),
        "unknown_tail_rows": int((result["source"] == "unknown_tail").sum()),
        "bridged_rows": int((result["source"] == "bridged_assumed").sum()),
        "gross_purchase_units": float(result["gross_qty_sold"].sum()),
        "returned_units": float(result["returned_qty"].sum()),
        "raw_quantity_units": float(result["raw_qty_sold"].sum()),
    })
    return result, stats
