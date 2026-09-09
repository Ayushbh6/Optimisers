# Phase 3 — Hierarchical Intermittent Demand Forecasting

> **Deliverable:** `artifacts/forecast.parquet`  
> **Test Suite:** `tests/test_phase3.py`  
> **Pipeline Entrypoint:** `python -m src.forecast.build_forecast`

---

## 1. Objective

Retail demand at the single SKU-store level is highly intermittent (~1 sale every few months) with severe sparsity. Single SKU series lack sufficient signal to fit traditional time-series models.

Phase 3 aggregates demand hierarchically to the `(Product Subcategory × Store × Week)` level to borrow statistical strength across related products, fits explainable intermittent demand models (**Croston** / **TSB**), calculates prediction intervals, and disaggregates back down to individual SKUs using historical shares with Laplace smoothing.

---

## 2. Methodology

### 2.1 Temporal & Hierarchical Aggregation
- **Temporal:** Daily unconstrained demand from Phase 2 is aggregated into weekly buckets aligned on Monday (`W-MON`), producing 48 chronological weeks across the 328-day timeline.
- **Hierarchy:** Aggregated to `(Product Subcategory × Store × Week)`, reducing 13.95M sparse daily records to 64,743 weekly points across 1,565 active subcategory-store series.

### 2.2 Forecasting Models
1. **Croston's Method:**
   - Separates demand into non-zero sizes ($z$) and inter-arrival periods ($p$).
   - Point forecast: $\hat{y} = \hat{z} / \hat{p}$.
2. **Teunter-Syntetos-Babai (TSB):**
   - Estimates demand probability $P_t$ in every period and demand size $z_t$.
   - Point forecast: $\hat{y} = P \times \hat{z}$.

### 2.3 Anti-Leakage Hold-Out Evaluation
- **Temporal Boundary:**
  - Training window: First 33 weeks (June 2025 – January 2026).
  - Test window: Final 15 weeks (January 2026 – April 2026).
  - Zero overlap between training and test sets.
- **Benchmark Against Naive Baseline:**
  - On **Scholar Footwear**, the model achieves:
    - **Global Portfolio MASE:** **0.9653** ($< 1.0$)
    - **Median Series MASE:** **0.9068** ($< 1.0$)
    - **Error Reduction:** **8.04% lower absolute error** than the naive baseline.

### 2.4 Top-Down Disaggregation
- Disaggregates aggregate forecasts $\hat{Y}_{\text{subcat}, s}$ down to SKU $i$ using Laplace-smoothed shares:
  $$\text{share}_i = \frac{D_i + \epsilon}{\sum_j (D_j + \epsilon)}, \quad \epsilon = 10^{-4}$$
- Reconciles exactly: $\sum_i \hat{y}_{i,s} = \hat{Y}_{\text{subcat}, s}$ (max difference $< 10^{-14}$).
- Scales uncertainty: $\sigma_i = \sqrt{\text{share}_i} \cdot \sigma_{\text{subcat}}$.

---

## 3. Artifact Schema (`artifacts/forecast.parquet`)

| Column | Type | Description |
|---|---|---|
| `Product No` | `string` | Unique SKU identifier |
| `Store` | `string` | Storefront identifier |
| `forecast_horizon_weeks` | `int64` | Projection horizon in weeks (default: 4) |
| `weekly_expected_demand` | `float64` | Expected weekly unconstrained demand |
| `daily_expected_demand` | `float64` | Expected daily demand rate ($\text{weekly} / 7$) |
| `demand_std` | `float64` | Weekly demand standard error |
| `lower_bound_95` | `float64` | Lower 95% prediction interval bound ($\ge 0$) |
| `upper_bound_95` | `float64` | Upper 95% prediction interval bound |
| `method` | `string` | Model algorithm (`croston` or `tsb`) |
| `aggregate_level` | `string` | Hierarchy aggregation tier (`Subcategory`) |

---

## 4. Execution & Verification

```bash
# Run Phase 3 Pipeline
python -m src.forecast.build_forecast

# Run Phase 3 Tests
pytest tests/test_phase3.py -v
```
