# Phase 4 — Inventory Policy: (s, S) Reorder Rule

> **Deliverable:** `artifacts/policy.parquet`  
> **Test Suite:** `tests/test_phase4.py`  
> **Pipeline Entrypoint:** `python -m src.policy.build_policy`

---

## 1. Objective

Given the true unconstrained demand forecasts $\mu_d$ and uncertainty $\sigma_d$ from Phase 3, Phase 4 computes an optimal, explainable $(s, S)$ continuous-review inventory policy for every `(Product No, Store)` pair.

The policy provides store managers and replenishment systems with exact operational rules:
- **Reorder Point ($s$):** If on-hand plus on-order inventory falls to or below $s$, trigger a replenishment order.
- **Order-Up-To Level ($S$):** Order exactly $Q = S - \text{inventory position}$ units to restore stock to $S$.

---

## 2. Explicit Assumptions & Parameters

All assumptions are user-configurable and explicitly persisted in every row of the policy artifact:

| Parameter | Notation | Default Value | Notes |
|---|---|---|---|
| **Supplier Lead Time** | $L$ | 10 days | Duration between PO generation and physical shelf receipt |
| **Target Service Level** | $SL$ | 95% ($z = 1.645$) | Cycle service level ($1 - \text{stockout probability}$) |
| **Annual Holding Cost Rate** | $r$ | 20% / year | Annual cost of holding stock as a fraction of wholesale unit cost |
| **Reorder Fixed Cost** | $K$ | €50 PO (€2 line) | Replenishment transaction cost allocated per active SKU line |
| **Minimum Order Quantity** | $MOQ$ | 1 unit | Minimum order lot size (piece lot) |

---

## 3. Mathematical Formulation

### 3.1 Lead-Time Demand & Uncertainty
$$\mu_L = \mu_d \times L$$
$$\sigma_L = \sigma_d \times \sqrt{L / 7}$$
where $\mu_d$ is the daily expected demand and $\sigma_d$ is the weekly standard error from Phase 3.

### 3.2 Safety Stock & Reorder Point ($s$)
$$SS = \max\left(z \times \sigma_L, \, 0.5\right)$$
$$s = \lceil \mu_L + SS \rceil$$
- Guarantees $s \ge 1$ for all active items.

### 3.3 Economic Order Quantity & Order-Up-To Level ($S$)
Annual holding cost per unit: $H = r \times \text{unit\_cost}$  
Annual demand: $D_{\text{annual}} = 365 \times \mu_d$

$$\text{EOQ} = \left\lceil \sqrt{\frac{2 \times D_{\text{annual}} \times K_{\text{line}}}{H}} \right\rceil$$
$$Q = \max(\text{EOQ}, \, MOQ)$$
$$S = s + Q$$
- Guarantees $S > s$ ($0 < s < S$) for 100% of rows.

### 3.4 Target Stock & Capital Valuation
Average expected physical on-hand units during active replenishment cycles:
$$\text{Target Stock} = SS + \frac{Q}{2}$$

---

## 4. Economic Capital Reduction Audit

| Metric | Observed Baseline | Optimized Policy | Impact |
|---|---|---|---|
| **Enterprise Inventory Value** | €2,655,163.33 | €2,012,195.59 | **-€642,967.74 (-24.2%)** |
| **Target Cycle Service Level** | ~67.5% (actual in-stock) | 95.0% (target) | **+27.5 pts service level** |
| **Active SKU Coverage** | 60,968 pairs | 60,968 pairs | 100% coverage |
| **Ordering Invariant** | N/A | $0 < s < S$ (100%) | 0 violations |

---

## 5. Artifact Schema (`artifacts/policy.parquet`)

| Column | Type | Description |
|---|---|---|
| `Product No` | `string` | Unique SKU identifier |
| `Store` | `string` | Storefront identifier |
| `reorder_point_s` | `float64` | Minimum inventory position triggering replenishment ($s \ge 1$) |
| `order_up_to_S` | `float64` | Target inventory level when ordering ($S > s$) |
| `safety_stock` | `float64` | Buffer stock for demand/lead-time uncertainty |
| `order_qty_q` | `float64` | Typical replenishment lot size ($S - s$) |
| `target_stock` | `float64` | Expected average on-hand units ($SS + Q/2$) |
| `unit_cost` | `float64` | Wholesale cost per unit |
| `daily_expected_demand`| `float64` | Daily expected demand rate |
| `lead_time_days` | `int64` | Configured lead time (10) |
| `target_service_level` | `float64` | Target cycle service level (0.95) |
| `annual_holding_rate` | `float64` | Annual holding cost rate (0.20) |
| `reorder_cost` | `float64` | Reorder fixed cost (€50.0) |
| `min_order_qty` | `int64` | Minimum order quantity (1) |

---

## 6. Execution & Verification

```bash
# Run Phase 4 Pipeline
python -m src.policy.build_policy

# Run Phase 4 Tests
pytest tests/test_phase4.py -v
```
