"""Daily on-hand stock reconstruction engine for enterprise retail inventory.

Transforms SCD Type 2 inventory validity intervals into contiguous, gap-free daily snapshots
per (Product No, Store), resolves interval conflicts, and reconciles unobserved gaps with
the cash register sales ledger.
"""

import logging
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

from src.data.config import DEFAULT_CONFIG, DataConfig
from src.data.loader import aggregate_daily_sales

logger = logging.getLogger(__name__)


def expand_inventory_intervals(
    inv_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Vectorized expansion of SCD Type 2 intervals into daily records.

    Applies the non-negative flooring policy for negative raw on-hand values
    and resolves any interval overlaps by preferring the later Start Date.

    Args:
        inv_df: Raw inventory ledger with parsed Start Date and End Date_parsed.

    Returns:
        Tuple containing:
            - pd.DataFrame: Daily expanded records with source='observed'.
            - Dict[str, Any]: Audit statistics of the expansion process.
    """
    logger.info("Expanding %d SCD Type 2 inventory intervals to daily records...", len(inv_df))

    # Audit raw negative inventory records before flooring
    raw_negatives_mask = inv_df["Qty on hand"] < 0
    raw_negatives_count = int(raw_negatives_mask.sum())
    min_raw_qty = float(inv_df["Qty on hand"].min())

    # Calculate duration of each interval in calendar days (inclusive of both endpoints)
    durations = (inv_df["End Date_parsed"] - inv_df["Start Date"]).dt.days + 1
    if (durations < 1).any():
        invalid = (durations < 1).sum()
        raise ValueError(f"Found {invalid} intervals with duration < 1 day.")

    days_array = durations.to_numpy()
    total_expanded_rows = int(days_array.sum())

    # Fast vectorized repetition across interval durations
    rep_idx = np.repeat(np.arange(len(inv_df)), days_array)
    interval_starts = np.zeros(len(days_array), dtype=np.int64)
    interval_starts[1:] = np.cumsum(days_array[:-1])
    day_offsets = np.arange(total_expanded_rows) - np.repeat(interval_starts, days_array)

    expanded_dates = inv_df["Start Date"].to_numpy()[rep_idx] + day_offsets.astype("timedelta64[D]")

    # Floored non-negative on-hand array
    floored_qty = np.maximum(0.0, inv_df["Qty on hand"].to_numpy()[rep_idx]).astype(np.float64)

    expanded = pd.DataFrame(
        {
            "Product No": inv_df["Product No"].to_numpy()[rep_idx],
            "Store": inv_df["Store"].to_numpy()[rep_idx],
            "date": expanded_dates,
            "qty_onhand": floored_qty,
            "unit_cost": inv_df["Stock Unit Cost Price"].to_numpy()[rep_idx].astype(np.float64),
            "unit_selling_price": inv_df["Stock Unit Selling Price"].to_numpy()[rep_idx].astype(np.float64),
            "stock_status": inv_df["Stock Status"].to_numpy()[rep_idx],
            "start_date_ref": inv_df["Start Date"].to_numpy()[rep_idx],
            "source": "observed",
        }
    )

    # Resolve overlaps/conflicts defensively: if multiple intervals cover the same date,
    # keep the one with the later Start Date and log conflict occurrences.
    duplicate_mask = expanded.duplicated(subset=["Product No", "Store", "date"], keep=False)
    conflicts_count = int(duplicate_mask.sum())
    if conflicts_count > 0:
        logger.warning(
            "Found %d overlapping daily records across intervals. Resolving by later Start Date...",
            conflicts_count,
        )
        expanded = (
            expanded.sort_values(["Product No", "Store", "date", "start_date_ref"])
            .drop_duplicates(subset=["Product No", "Store", "date"], keep="last")
            .reset_index(drop=True)
        )
    else:
        logger.info("Verified: 0 interval overlaps in observed inventory records.")

    expanded.drop(columns=["start_date_ref"], inplace=True)

    stats = {
        "raw_intervals_count": len(inv_df),
        "expanded_observed_rows": len(expanded),
        "raw_negative_records_floored": raw_negatives_count,
        "min_raw_qty_before_flooring": min_raw_qty,
        "conflicts_resolved": conflicts_count,
    }
    return expanded, stats


def reconstruct_daily_onhand(
    inv_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    config: DataConfig = DEFAULT_CONFIG,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Reconstruct complete, gap-free daily on-hand inventory per (Product No, Store).

    For every pair with >=1 inventory record, builds a contiguous daily timeline from
    its first observed inventory date through the observation horizon end (2026-04-24).
    Gaps between intervals and post-depletion periods are reconstructed using daily sales:
    carrying forward the previous known on-hand and decrementing by net sales (floored at 0).

    Args:
        inv_df: Cleaned inventory interval records.
        sales_df: Raw sales ledger.
        config: System data configuration.

    Returns:
        Tuple containing:
            - pd.DataFrame: Full contiguous daily on-hand table.
            - Dict[str, Any]: Detailed execution and reconciliation metrics.
    """
    logger.info("Starting Phase 1 daily on-hand reconstruction pipeline...")

    # 1. Expand observed intervals and resolve any duplicates/negatives
    expanded_obs, expansion_stats = expand_inventory_intervals(inv_df)

    # 2. Aggregate net daily sales per (Product No, Store, Date)
    daily_sales = aggregate_daily_sales(sales_df)
    daily_sales = daily_sales.rename(columns={"net_qty_sold": "sales_qty"})

    # 3. Determine active span per (Product No, Store) pair with >=1 inventory record
    pair_starts = (
        inv_df.groupby(["Product No", "Store"])["Start Date"]
        .min()
        .reset_index()
        .sort_values(["Product No", "Store"])
        .reset_index(drop=True)
    )

    horizon_end = pd.to_datetime(config.observation_end_date)
    pair_starts["span_days"] = (horizon_end - pair_starts["Start Date"]).dt.days + 1

    # 4. Generate the complete contiguous daily grid across active spans
    span_days = pair_starts["span_days"].to_numpy()
    total_grid_rows = int(span_days.sum())

    rep_idx = np.repeat(np.arange(len(pair_starts)), span_days)
    grid_starts = np.zeros(len(span_days), dtype=np.int64)
    grid_starts[1:] = np.cumsum(span_days[:-1])
    grid_offsets = np.arange(total_grid_rows) - np.repeat(grid_starts, span_days)
    grid_dates = pair_starts["Start Date"].to_numpy()[rep_idx] + grid_offsets.astype("timedelta64[D]")

    grid_df = pd.DataFrame(
        {
            "Product No": pair_starts["Product No"].to_numpy()[rep_idx],
            "Store": pair_starts["Store"].to_numpy()[rep_idx],
            "date": grid_dates,
        }
    )

    logger.info(
        "Generated full contiguous grid for %d pairs: %d total calendar rows.",
        len(pair_starts),
        len(grid_df),
    )

    # 5. Merge observed daily records onto the contiguous grid
    merged = grid_df.merge(
        expanded_obs,
        on=["Product No", "Store", "date"],
        how="left",
    )

    # 6. Merge net daily sales onto the grid
    merged = merged.merge(
        daily_sales[["Product No", "Store", "date", "sales_qty"]],
        on=["Product No", "Store", "date"],
        how="left",
    )
    merged["sales_qty"] = merged["sales_qty"].fillna(0.0).astype(np.float64)

    # 7. Forward-fill pricing, cost, and catalog status across gaps
    merged["unit_cost"] = merged["unit_cost"].ffill().bfill()
    merged["unit_selling_price"] = merged["unit_selling_price"].ffill().bfill()
    merged["stock_status"] = merged["stock_status"].ffill().bfill()

    # 8. Reconstruct on-hand stock and source flags across unobserved intervals
    is_pair_start = np.zeros(len(merged), dtype=bool)
    is_pair_start[grid_starts] = True

    # Identify last active date per pair (last observed inventory or last sale)
    # Beyond the last active date, a product is retired/exhausted and does not hold ghost stock
    last_obs = expanded_obs.groupby(["Product No", "Store"])["date"].max()
    last_sales = daily_sales[daily_sales["sales_qty"] > 0].groupby(["Product No", "Store"])["date"].max()
    last_active_lookup = pd.concat([last_obs, last_sales], axis=1).max(axis=1).to_dict()

    qty_array = merged["qty_onhand"].to_numpy(copy=True)
    sales_array = merged["sales_qty"].to_numpy()
    is_observed_mask = (merged["source"] == "observed").to_numpy()
    dates_array = merged["date"].to_numpy()
    products_array = merged["Product No"].to_numpy()
    stores_array = merged["Store"].to_numpy()
    horizon_end = pd.to_datetime(config.observation_end_date)

    logger.info("Executing forward reconstruction loop over %d daily records...", len(qty_array))

    # Single sequential pass per pair to reconcile gaps with net sales
    for i in range(len(qty_array)):
        if is_pair_start[i]:
            if not is_observed_mask[i]:
                # If first day in span lacked observed record, initialize at 0
                qty_array[i] = 0.0
        else:
            if not is_observed_mask[i]:
                # If date is past the product's last active date, it is retired/exhausted (shelf stock = 0)
                p = products_array[i]
                s = stores_array[i]
                d = dates_array[i]
                if d > last_active_lookup.get((p, s), horizon_end):
                    qty_array[i] = 0.0
                else:
                    # Gap day: carry forward previous on-hand, decrement by net sales, floor at 0
                    qty_array[i] = max(0.0, qty_array[i - 1] - sales_array[i])

    merged["qty_onhand"] = qty_array
    merged["source"] = np.where(is_observed_mask, "observed", "reconstructed")

    # Final cleanup and schema conformation
    result_df = merged[list(config.daily_onhand_columns)].copy()

    # Format numeric types
    result_df["qty_onhand"] = result_df["qty_onhand"].round(4)
    result_df["unit_cost"] = result_df["unit_cost"].round(4)
    result_df["unit_selling_price"] = result_df["unit_selling_price"].round(4)

    summary_stats = {
        **expansion_stats,
        "total_pairs_reconstructed": len(pair_starts),
        "total_daily_rows": len(result_df),
        "observed_rows_count": int((result_df["source"] == "observed").sum()),
        "reconstructed_rows_count": int((result_df["source"] == "reconstructed").sum()),
        "distinct_products": int(result_df["Product No"].nunique()),
        "distinct_stores": int(result_df["Store"].nunique()),
        "min_date": str(result_df["date"].min().date()),
        "max_date": str(result_df["date"].max().date()),
    }

    logger.info(
        "Reconstruction finished: %d observed rows, %d reconstructed rows. Total: %d",
        summary_stats["observed_rows_count"],
        summary_stats["reconstructed_rows_count"],
        summary_stats["total_daily_rows"],
    )

    return result_df, summary_stats
