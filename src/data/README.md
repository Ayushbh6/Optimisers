# Phase 1 — Daily On-Hand Stock Reconstruction

> **Deliverable:** `artifacts/daily_onhand.parquet`  
> **Test Suite:** `tests/test_phase1.py`  
> **Pipeline Entrypoint:** `python -m src.data.build_daily_onhand`

---

## 1. Objective

Turn the raw slowly-changing dimension (SCD Type 2) inventory intervals (`data/raw/retail_inventory_ml_apl.csv`) and the cash register sales transactions (`data/raw/retail_sales_ml_apl.csv`) into an authoritative, contiguous **daily snapshot**: for every `(Product No, Store)` pair and every day in its active timeline, exactly how many units were on hand.

---

## 2. Documented Policies & Business Logic

### 2.1 The `9999-12-31` Sentinel Policy
- **Background:** The raw inventory ledger contains 22,701 open-ended validity intervals where `End Date = 9999-12-31`. These represent inventory states that were still current at the time of the data extraction.
- **Policy:** For the purpose of interval expansion, the sentinel `9999-12-31` is capped at the observation horizon end date (`2026-04-24`).
- **Invariants:** 
  - All `9999-12-31` records are verified to be the final chronological record for their respective `(Product No, Store)`.
  - The retrospective `End Date` column is never leaked to forecasting models or decision rules in downstream phases.

### 2.2 Overlap and Conflict Resolution Policy
- **Background:** When combining interval-based inventory records, overlapping date ranges for the same entity create ambiguous shelf counts.
- **Audit Finding:** The raw inventory ledger has **0 interval overlaps** (`diff_to_next >= 1` across all 284,755 rows).
- **Defensive Rule:** In `expand_inventory_intervals()`, if two records ever claim coverage for the same `(Product No, Store, date)`, the engine sorts by `Start Date` ascending and retains the record with the **later `Start Date`**, logging any conflicts.

### 2.3 Unobserved Gaps and Post-Depletion Reconstruction Policy
- **Background:** In retail ERP systems, when an SKU depletes its last on-hand unit to 0, the system closes the interval on the day before the stockout ($D - 1$) and does not write continuous 0-quantity rows. This accounts for:
  - 22,898 sales occurring after the last recorded inventory date.
  - 9,196 sales occurring in temporary stockout gaps between replenishment waves.
- **Active Span Definition:** Each `(Product No, Store)` pair's active span begins at its first recorded inventory date ($\min(\text{Start Date})$) and runs through the horizon end date (`2026-04-24`).
- **Reconstruction Algorithm:**
  1. For days covered by an inventory interval: shelf count is directly observed (`source = 'observed'`).
  2. For days inside gaps or post-interval windows:
     - On day $t$, on-hand is initialized from day $t-1$: $H_{t-1}$.
     - If customer sales or returns occurred on day $t$ ($S_t$), on-hand is decremented: $H_t = \max(0, H_{t-1} - S_t)$.
     - If no sales occurred: $H_t = H_{t-1}$ (which is $0$ if already depleted).
     - Catalog attributes (`unit_cost`, `unit_selling_price`, `stock_status`) are forward-filled.
     - The record is flagged as `source = 'reconstructed'`.

### 2.4 Negative Inventory Policy (`Qty on hand < 0`)
- **Background:** In the raw inventory ledger, 1,380 rows record negative quantities (ranging from $-9$ to $-1$, predominantly caused by cashier sales occurring before warehouse check-in scanning).
- **Policy:** 
  - Physical shelves cannot hold negative stock. All `Qty on hand < 0` values are floored to `0.0`.
  - The count of floored rows (1,380) and minimum raw value ($-9.0$) are recorded in the audit log so no raw ledger behavior is silently masked.

### 2.5 Sales Depletion Reconciliation Rate
- **Criterion:** $\ge 90\%$ of net sales volume must match a same-day inventory step-down (within $\pm 1$ day tolerance).
- **Results Achieved:**
  - Total Enterprise Net Sales: **116,995.0 units** across 123,928 daily sales dates.
  - Exact Same-Day Matched Volume: **105,466.0 units** (**90.15%**).
  - Tolerance Matched Volume ($\pm 1$ day window): **106,021.0 units** (**90.62%**).
  - Both pass the 90.0% threshold.

---

## 3. Artifact Data Dictionary (`artifacts/daily_onhand.parquet`)

| Column | Type | Description |
|---|---|---|
| `Product No` | `string` | Distinct SKU identifier (`PROD-100043` to `PROD-170517`) |
| `Store` | `string` | Storefront identifier (`STR-1006` to `STR-1369`) |
| `date` | `timestamp` | Daily calendar date (`2025-06-01` through `2026-04-24`) |
| `qty_onhand` | `float64` | Authoritative physical on-hand unit count ($\ge 0$) |
| `unit_cost` | `float64` | Wholesale cost per unit |
| `unit_selling_price` | `float64` | Current retail price per unit |
| `stock_status` | `string` | Pricing regime (`Full Price`, `Promo`, `Markdown Tier 1`, etc.) |
| `source` | `string` | Provenance of record: `'observed'` vs `'reconstructed'` |

---

## 4. Execution & Verification

### Build the Artifact
```bash
python -m src.data.build_daily_onhand
```

### Run Validation Tests
```bash
pytest tests/test_phase1.py -v
```
