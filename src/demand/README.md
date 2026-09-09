# Phase 2 — True (Unconstrained) Demand Estimation

> **Deliverable:** `artifacts/demand.parquet`  
> **Test Suite:** `tests/test_phase2.py`  
> **Pipeline Entrypoint:** `python -m src.demand.build_demand`

---

## 1. Objective

When a retail storefront runs out of physical shelf stock (`qty_onhand == 0`), recorded cash register sales drop to 0. Treating these zero-sales days as zero true demand introduces severe negative bias into downstream forecasting models, causing systemic under-replenishment and perpetual stockouts.

Phase 2 identifies all stockout-censored observation windows and reconstructs an explainable, authoritative estimate of **unconstrained customer demand** across all 13,950,817 active `(Product No, Store, date)` records.

---

## 2. Methodology & Business Rules

### 2.1 Censoring Identification
- **Criterion:** A record on calendar date $t$ for product $p$ at store $s$ is defined as censored:
  $$\text{is\_censored}_{p,s,t} \iff \text{qty\_onhand}_{p,s,t} = 0$$
- Across the enterprise timeline, **4,533,616 days (32.50%)** are identified as stockout-censored periods.

### 2.2 In-Stock Baseline Demand Rate Estimation
For each product and store, baseline sales velocity is estimated exclusively from non-censored (in-stock) observation days:
$$\text{Clean Demand}_{p,s,t} = \max(0, \text{observed\_sales}_{p,s,t})$$

Negative sales days (where return volume exceeded sales) are floored at 0.0 when computing in-stock demand rates, preventing customer returns from falsely depressing real customer purchasing appetite.

### 2.3 Hierarchical Imputation Fallback
When a pair enters a stockout window, true demand is estimated using an explainable multi-tier fallback:

| Tier | Method Tag | Description | Condition | Count in Dataset |
|---|---|---|---|---|
| **Tier 0** | `observed` | Uncensored in-stock day; observed demand is trusted | `qty_onhand > 0` | 9,417,201 (67.50%) |
| **Tier 1** | `sku_store_in_stock_mean` | Historical in-stock daily mean for that SKU at that store | In-stock days $\ge 7$ | 4,085,283 (29.28%) |
| **Tier 2** | `sku_global_in_stock_mean` | Enterprise-wide in-stock daily mean for that SKU across all stores | In-stock days $\ge 7$ network-wide | 448,333 (3.21%) |
| **Tier 3** | `subcategory_store_in_stock_mean` | In-stock daily rate for SKU's Subcategory at that store | Subcategory in-stock days $\ge 7$ | 0 (fallback not needed) |
| **Tier 4** | `subcategory_global_in_stock_mean` | Enterprise-wide in-stock rate for SKU's Subcategory | Chain-wide subcategory rate | 0 (fallback not needed) |
| **Tier 5** | `zero_floor` | Strict non-negative floor ($0.0$) | No valid history anywhere | 0 (fallback not needed) |

### 2.4 Unconstrained Demand Assignment
For every record:
1. **Uncensored days:**
   $$\text{unconstrained\_demand} = \max(0.0, \text{observed\_demand})$$
2. **Censored days:**
   $$\text{unconstrained\_demand} = \max(\text{observed\_demand}, \text{imputed\_rate}, 0.0)$$

This guarantees:
- `unconstrained_demand >= observed_demand` everywhere (0 violations across 13.95M rows).
- `unconstrained_demand >= 0.0` everywhere.
- If an anomalous sale occurred during a zero-onhand record, unconstrained demand is never lower than the actual units sold.

---

## 3. Uplift Audit & Magnitude Summary

| Metric | Value |
|---|---|
| Total Observed Demand | 113,466.0 units |
| Total Unconstrained Demand | 228,033.9 units |
| Net Unconstrained Uplift | +114,567.9 units (+100.97%) |
| Share of Uplift from Stockout Windows | **95.06%** (108,908.9 units) |
| Share of Uplift from Return Flooring | **4.94%** (5,659.0 units) |

The uplift is strictly concentrated in stockout periods as required by `PLAN.md`.

---

## 4. Artifact Schema (`artifacts/demand.parquet`)

| Column | Type | Nullable | Description |
|---|---|---|---|
| `Product No` | `string` | No | Unique SKU identifier |
| `Store` | `string` | No | Store identifier |
| `date` | `timestamp` | No | Calendar date |
| `observed_demand` | `float64` | No | Raw net units sold (sales minus returns) |
| `unconstrained_demand` | `float64` | No | Reconstructed unconstrained demand ($\ge 0$) |
| `is_censored` | `bool` | No | `True` iff `qty_onhand == 0` |
| `imputation_method` | `string` | No | Imputation tier provenance (`observed`, `sku_store_in_stock_mean`, `sku_global_in_stock_mean`, etc.) |

---

## 5. Execution & Verification

### Run the Pipeline
```bash
python -m src.demand.build_demand
```

### Run Phase 2 Tests
```bash
pytest tests/test_phase2.py -v
```
