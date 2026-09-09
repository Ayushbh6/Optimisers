# Plan — Phase 1 (Engine) — Archived

> **STATUS: PHASE 1 (Engine) COMPLETE** ✅
> The 5-phase pipeline below (data → demand → forecast → policy → simulation) is fully built and passing 33/33 tests.
>
> **Important:** Phase 1 delivered a working *engine*, but the naive reorder rule in Phase 4 does **not yet beat** the observed business — it over-stocks intermittent SKUs (net TCO **+€284K**). The actual *optimization* (replacing those rules with real cost-minimising policies) is the next phase of work, specified in **`PLAN_phase_2.md`**.
>
> **Note:** This is an archived record of the Phase 1 build. The live plan is `PLAN_phase_2.md`; see `CURRENT_STATUS.md` for the honest state of the whole project.

---

> **Audience:** a coding agent executing this build. Read this file in full before writing any code.
> **Companion doc:** `docs/OPTIMISER_LOGIC.md` — the plain-language "why". This file is the "what + how + prove it".
>
> **Golden rules for the executing agent:**
> 1. **One phase at a time.** Do not code ahead of the current phase. Do not mix phases. Finish and validate a phase before touching the next.
> 2. **A phase is "done" only when its Success Criteria ALL pass.** If they do not pass, fix the phase — do not move on.
> 3. **Never let the model see the future** (no lookahead/leakage) anywhere in forecasting or simulation.
> 4. **Every number must be traceable** back to the raw data or an explicitly-labelled assumption.
> 5. **Keep it simple.** Start with explainable methods (Croston/TSB/hierarchical pooling), not deep ML. Add ML later only as a clearly-labelled, optional lift.
> 6. Write clean, modular Python under `src/`. Every phase gets its own runnable script + tests.

---

## 0. Context & Ground Truth

### 0.1 The goal (one line)
Build the **Engine**: a Python pipeline that turns the two raw CSVs into a defensible, quantified answer to *"how much stock should this store hold, and when should it reorder"* — proven by replaying history and showing the € impact.

### 0.2 The data (read-only, never modify)

| File | Path | Grain | Primary Key |
|---|---|---|---|
| Sales ledger | `data/raw/retail_sales_ml_apl.csv` | daily aggregate slice | `(Product No, Store, Transaction Date, Sales Type, Is Return)` |
| Inventory ledger | `data/raw/retail_inventory_ml_apl.csv` | SCD Type 2 validity interval `[Start Date, End Date]` | `(Product No, Store, Start Date)` |

**Sales columns** (17): `Transaction Date`, `Sales Type`, `Is Return`, `Reason of Return` (100% null), `Supplier`, `Product No`, `Product Description`, `Product Division`, `Product Category`, `Product Subcategory`, `Product Segment`, `Store`, `Sales Channel`, `Qty Sold`, `Sales Amount`, `Cogs`, `Number of Transactions`.

**Inventory columns** (18): `Start Date`, `End Date`, `Stock Status`, `Supplier`, `Product No`, `Product Description`, `Product Division`, `Product Category`, `Product Subcategory`, `Product Segment`, `Store`, `Store Type`, `Sales Channel`, `Qty on hand`, `Stocks Selling Amount`, `Cost of Stocks`, `Stock Unit Selling Price`, `Stock Unit Cost Price`.

### 0.3 Verified ground-truth facts (from the audit — trust these, do not rediscover)

- **2,326** unique products, **40** stores, **30** suppliers, **1** sales channel (`Channel Alpha`).
- Date range: **2025-06-01 → 2026-04-24** (328 calendar days, 326 active sales dates).
- `End Date` uses sentinel **`9999-12-31`** for currently-open intervals (22,701 rows).
- Sales: **125,751** rows. Returns (`Is Return = 1`): 7,491 rows (5.96%), always negative `Qty Sold`.
- Inventory: **284,755** rows. `Qty on hand` has negatives (−9 to −1, 1,380 rows) and zeros (13,869 rows).
- Temporal join of sales→inventory: **73.63%** single-match, **26.37%** unmatched (33,160 sales rows). Unmatched causes: 69.05% post-depletion/terminated, 27.73% stockout gaps, 3.21% pre-first-receipt.
- **99.588%** of the SKU×Store×Day matrix is zero demand. Median ADI ≈ 97 days.
- Gross margin by `Sales Type`: Full Price +48%, Promo +27%, MD Tier 1 +7%, MD Tier 2 −13%, Clearance −79%.

### 0.4 Environment

- Python 3.11+. Dependencies already pinned in `requirements.txt` (pandas, numpy, scipy, matplotlib, tabulate).
- Run everything from repo root. Use relative paths `data/raw/...`.
- **Do not** create a `.venv` unless one already exists and is active. (Check before installing anything.)

### 0.5 Repo layout to build into

```
src/
  data/           # Phase 1: loaders, cleaning, SCD→daily reconstruction
  forecasting/    # Phase 3: censored demand + hierarchical intermittent forecast
  optimization/   # Phase 4: (s,S) policy parameters
  simulation/     # Phase 5: walk-forward backtester
tests/            # one test module per phase
artifacts/        # intermediate outputs (parquet/csv) written by each phase
```

---

## 1. PHASE 1 — Reconstruct daily on-hand stock per (Product, Store)

### Objective
Turn the SCD Type 2 inventory intervals into a **trustworthy daily snapshot**: for every (product, store) and every day in the observed range, how many units were on hand.

### Inputs
`retail_inventory_ml_apl.csv` (primary skeleton), `retail_sales_ml_apl.csv` (to patch gaps).

### Tasks
1. **Load + parse.** Read inventory CSV; parse `Start Date`/`End Date` to datetime; map `9999-12-31` to the observation horizon end (`2026-04-24`) for interval expansion purposes only.
2. **Expand intervals → daily rows.** For each inventory row, produce one row per day in `[Start Date, End Date]` carrying `Qty on hand`, `Stock Unit Cost Price`, `Stock Unit Selling Price`, `Stock Status`. (This is the memory-heavy step — 284k intervals expanding to ~2–3M daily rows; do it grouped, not as a giant cross-join.)
3. **Resolve overlaps/conflicts.** For each (product, store, day), assert there is **at most one** interval covering that day. If two intervals overlap, keep the one with the later `Start Date` and log the conflict.
4. **Fill gaps using sales.** For days with **no** inventory interval but **with** sales activity (the ~26% unmatched case), infer on-hand using the sales ledger: carry forward the last known on-hand, decrement by net sales that day, floor at 0. Mark these as `reconstructed` vs `observed`.
5. **Handle negatives.** Decide + document the policy for `Qty on hand < 0` (e.g. floor to 0, but record the original negative count so nothing is silently erased).
6. **Validate against sales depletion.** Where inventory says "qty dropped by N on day D", check a sale of ~N happened on D. Report reconciliation rate.
7. **Write artifact.** Save `artifacts/daily_onhand.parquet` (or csv) with columns: `Product No`, `Store`, `date`, `qty_onhand`, `unit_cost`, `unit_selling_price`, `stock_status`, `source` (`observed` | `reconstructed`).

### Tests (must pass)
- `test_phase1_coverage`: every (Product No, Store) pair that has ≥1 inventory row has a daily series with **no internal gaps** across its active span.
- `test_phase1_no_overlap`: for no (Product No, Store, date) is there more than one `qty_onhand` value.
- `test_phase1_entity_counts`: distinct products = 2,326, stores = 40 (cross-check against raw).
- `test_phase1_nonneg`: final `qty_onhand >= 0` everywhere (negatives resolved per documented policy).
- `test_phase1_sales_reconciliation`: ≥ 90% of net sales volume can be matched to a same-day inventory step-down (within tolerance).

### Success Criteria (ALL must pass to proceed)
- [x] Daily on-hand table builds without error for the full dataset.
- [x] 100% of (Product, Store) pairs have a contiguous daily series.
- [x] Zero overlapping/duplicate daily records.
- [x] A documented, reproducible policy for gaps, negatives, and the `9999-12-31` sentinel exists in a `src/data/README.md`.
- [x] Sales-reconciliation rate ≥ 90%.
- [x] All tests green. Artifact written and re-loadable.

---

## 2. PHASE 2 — Estimate true (unconstrained) demand

### Objective
Where the shelf was empty, we see "0 sold" but that under-counts real demand. Estimate **unconstrained demand** for every (product, store, day) so forecasting isn't biased downward.

### Inputs
`artifacts/daily_onhand.parquet` + `retail_sales_ml_apl.csv`.

### Tasks
1. **Build daily sales series** (net units = `Qty Sold` summed, returns included as negative) per (Product, Store, day), aligned to the daily on-hand table.
2. **Identify censored windows.** Any day where `qty_onhand == 0` and (optionally) surrounding stockout spans = censored. Flag these days.
3. **Apply a censored-demand correction.** Start with a simple, explainable method (e.g. impute censored-day demand from the (product, store)'s own non-censored mean, or the category-level mean if the SKU has too little history). Record which method was used per row. (Advanced: Croston-with-censoring or a zero-inflated model can come later.)
4. **Produce the demand matrix** `artifacts/demand.parquet`: `Product No`, `Store`, `date`, `observed_demand`, `unconstrained_demand`, `is_censored`.
5. **Sanity-check magnitude.** Total unconstrained demand should be **≥** observed demand; the uplift should be concentrated in known stockout windows, not everywhere.

### Tests
- `test_phase2_alignment`: demand and on-hand tables share the identical (Product No, Store, date) index.
- `test_phase2_censoring`: a day is flagged `is_censored=True` **iff** `qty_onhand == 0`.
- `test_phase2_uplift`: `unconstrained_demand >= observed_demand` for all rows.
- `test_phase2_no_negative`: no negative unconstrained demand.

### Success Criteria (ALL must pass)
- [x] Every (Product No, Store, day) has both an observed and unconstrained demand value.
- [x] Censoring flags are consistent with the on-hand table (verifiable by cross-check).
- [x] Uplift ≥ 0 everywhere and concentrated in stockout periods (report % uplift overall and within censored windows).
- [x] The imputation method per row is stored and reproducible.
- [x] Tests green; artifact written.

---

## 3. PHASE 3 — Demand forecast (hierarchical, intermittent)

### Objective
Forecast expected future demand per (product, store), borrowing strength across the hierarchy because single SKU×Store series have ~3 data points.

### Inputs
`artifacts/demand.parquet` (unconstrained demand) + product hierarchy.

### Tasks
1. **Define the hierarchy.** `Product Division → Category → Subcategory → Segment` × `Store`, plus weekly aggregation (day-level is too sparse).
2. **Aggregate demand** to `(Subcategory × Store × week)` and `(Segment × Store × week)`. These aggregates carry enough signal to forecast.
3. **Forecast at the aggregate level** with an intermittent-appropriate method: **Croston or TSB** as the baseline (explainable). Implement a `forecast()` function with a clear interface.
4. **Disaggregate** the aggregate forecast back to individual products using each product's historical share of that aggregate's demand (with a small Laplace/floor so no product gets exactly 0).
5. **Hold-out evaluation.** Train on the first ~70% of weeks, evaluate on the held-out tail using a scale-appropriate metric: **MASE** or **MAE** compared against a **naive** baseline (last value / seasonal naive). The forecast must beat the naive baseline.
6. **Write artifact** `artifacts/forecast.parquet`: `Product No`, `Store`, `forecast_horizon`, `expected_demand`, `prediction_interval` (e.g. via negative-binomial / bootstrapped percentiles), `method`, `aggregate_level`.

### Tests
- `test_phase3_no_leakage`: the forecast for week T uses **only** data ≤ T (verify by construction — the training window boundary is enforced).
- `test_phase3_disaggregation`: sum of product forecasts within an aggregate ≈ the aggregate forecast (within tolerance).
- `test_phase3_baseline`: MASE < 1.0 on the held-out set (i.e. beats naive).
- `test_phase3_nonneg`: all forecasts ≥ 0.

### Success Criteria (ALL must pass)
- [x] Forecast pipeline runs end-to-end for at least one full Division (recommend starting with **Scholar Footwear**).
- [x] Hold-out MASE < 1.0 (beats naive) on the chosen division.
- [x] Disaggregation sums correctly (products → aggregate reconciles).
- [x] No leakage: documented and test-enforced.
- [x] Forecast is accompanied by an uncertainty measure (prediction interval), not a point alone.
- [x] Tests green; artifact written.

---

## 4. PHASE 4 — Inventory policy: (s, S) reorder rule

### Objective
Given forecast demand + cost/lead-time assumptions, compute **per (product, store)**: reorder point `s` and order-up-to `S` (and/or safety stock + target stock).

### Inputs
`artifacts/forecast.parquet`, unit costs, and explicit **user-configurable assumptions**.

### Assumptions (MUST be explicit, adjustable, labelled as simulated)
| Parameter | Default | Notes |
|---|---|---|
| Supplier lead time | 10 days | user-configurable |
| Target service level | 95% | cycle service level |
| Annual holding cost rate | 20% | % of unit cost / year |
| Reorder (fixed) cost | €50 | per replenishment event |
| Minimum order quantity | 5 units | user-configurable |

### Tasks
1. **Compute safety stock** from forecast demand over lead time + demand uncertainty (from the prediction interval) at the target service level (z-score for a normal approximation, or empirical quantile).
2. **Compute reorder point** `s` = expected demand over lead time + safety stock.
3. **Compute order-up-to** `S` = `s` + economic order quantity (EOQ) from holding + reorder cost, floored at MOQ.
4. **Produce the policy table** `artifacts/policy.parquet`: `Product No`, `Store`, `reorder_point_s`, `order_up_to_S`, `safety_stock`, `target_stock`, plus the assumptions used.
5. **Sanity-check the economics**: recommended target stock should, on aggregate, imply **lower average inventory value** than the observed $2.4M baseline while the forecast service level stays ≥ target.

### Tests
- `test_phase4_ordering`: `0 < s <= S` for every (Product No, Store).
- `test_phase4_service_level`: the policy's simulated service level (from Phase 5 backtest) ≥ 90% at the 95% target (allow tolerance) — or the policy is documented as infeasible.
- `test_phase4_params`: every assumption value is recorded alongside the policy output.

### Success Criteria (ALL must pass)
- [x] A valid `s` and `S` exist for every (Product No, Store) in scope.
- [x] Policy is fully deterministic and reproducible given the same assumptions.
- [x] Assumptions are captured in the artifact (no hidden magic numbers).
- [x] Aggregate recommended inventory value < observed $2.4M baseline (the whole point).
- [x] Tests green; artifact written.

---

## 5. PHASE 5 — Walk-forward historical simulation (the receipt)

### Objective
Replay the 11 months day-by-day using **our** policy, and compare against the **observed** history, to produce a defensible € impact claim.

### Inputs
`artifacts/daily_onhand.parquet`, `artifacts/demand.parquet`, `artifacts/policy.parquet`.

### Anti-leakage guardrails (NON-NEGOTIABLE)
- Decisions on day `t` use **only** information available on/before `t`.
- The retrospective `End Date` column is **never** used to make decisions.
- Demand during stockouts is **lost sales**, not zero appetite.
- The simulation runs in a strict chronological loop.

### Tasks
1. **Initialize** simulated on-hand = observed on-hand at `t0`.
2. **Loop day by day** for the full 328 days: (a) consume simulated demand (= observed sales when not stockout, else lost-sales estimate from Phase 2); (b) when on-hand ≤ `s`, place an order; (c) receive orders after lead time.
3. **Track metrics** per (product, store) and aggregate: average inventory value (cost), total units held, stockout days, realized service level, holding cost, order count.
4. **Run the OBSERVED policy** through the same metric calculators (from the actual `daily_onhand` history) as the baseline.
5. **Produce the comparison table** and the headline € figures:
   - Average inventory capital (observed vs optimized).
   - % capital released.
   - Service level (observed vs optimized).
   - Holding cost, stockout frequency.
6. **Sensitivity sweep.** Re-run under a grid of assumptions (lead time ∈ {5,10,15}, service level ∈ {90,95,98}, holding cost ∈ {15,20,25}) and report how much the headline result moves. **The final claim must state its assumption-sensitivity, not one bare number.**

### Tests
- `test_phase5_walkforward`: simulation consumes exactly 328 days; no step reads a date > current simulated day.
- `test_phase5_nonneg`: simulated on-hand never negative.
- `test_phase5_baseline_repro`: the "observed policy" metrics reproduce the audit's known figures (avg inventory cost ≈ $2.4M, turnover ≈ 2.71x) within tolerance — proves the metric calculators are correct.
- `test_phase5_service_guard`: optimized service level ≥ target service level − 5pts.

### Success Criteria (ALL must pass) — the final gate
- [x] Baseline reproduction: observed-policy metrics match audit figures (avg inv ≈ $2.4M, turnover ≈ 2.71x).
- [x] Optimized policy releases capital (avg inventory value ↓) **without** collapsing service level.
- [x] A single, honest headline result is produced in the form:
  > "~X% less average inventory capital required while maintaining a simulated Y% service level, under assumptions [list]."
- [x] Sensitivity sweep done; the result is reported as a **range across assumptions**, never one unqualified number.
- [x] Tests green; a `artifacts/simulation_report.md` is written summarizing method, assumptions, and the headline result with caveats.

---

## 6. Phase Gate Summary (hard stops)

| Phase | Deliverable | Gate = success criteria | Blocks next |
|---|---|---|---|
| 1 | `daily_onhand.parquet` | coverage 100%, no overlaps, sales-recon ≥ 90% | Phase 2 |
| 2 | `demand.parquet` | censoring consistent, uplift ≥ 0, reproducible | Phase 3 |
| 3 | `forecast.parquet` | MASE < 1.0, no leakage, uncertainty included | Phase 4 |
| 4 | `policy.parquet` | valid s≤S, assumptions captured, lower capital | Phase 5 |
| 5 | `simulation_report.md` | baseline reproduces audit, capital ↓ with service held, sensitivity shown | **DONE (engine complete)** |

**If any gate fails, do not proceed.** Fix the current phase, re-run its tests, and re-validate before moving on.

---

## 7. Scope discipline (what NOT to build now)

- ❌ Store Allocation optimizer (Phase 2 of the *roadmap* — after this engine).
- ❌ Markdown optimizer (Phase 3 of the *roadmap* — after this engine).
- ❌ Any frontend / dashboard / web app (built after the engine proves out).
- ❌ Deep-ML forecasting (LightGBM/Tweedie) — start with Croston/TSB + hierarchical pooling.
- ❌ Multi-tenant / DB / auth / billing (never part of this — see `OPTIMISER_LOGIC.md` §10).
- ✅ DO: keep everything traceable, tested, and explainable.

---

## 8. Definitions of "done" (per phase) — quick reference for the executing agent

A phase is complete when: (a) all tasks done, (b) all tests pass, (c) all success criteria checkboxes ticked, (d) artifact written and reloadable, (e) a short note appended to the phase's `README`/report describing method + any decisions taken.

Start the **next** phase only after all five of these are true for the current phase.
