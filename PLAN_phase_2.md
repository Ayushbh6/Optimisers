# PLAN_phase_2.md — Retail Optimiser: The Actual Optimization

> **Status:** THE ACTIVE PLAN. Phase 1 (the engine/pipeline) is complete — see `CURRENT_STATUS.md`.
> **Goal:** Replace the naive "enforce 95% service" rules with a **real optimizer** that produces a positive, defensible "X% less capital" result, displayable on the website.
> **Audience:** the coding agent + the two founders. Read `CURRENT_STATUS.md` and `docs/OPTIMISER_LOGIC.md` first.
>
> **Golden rule for Phase 2:** the goal is no longer "make the pipeline run" — it's "make the *number* honest and positive, or prove why it can't be." No fabrication, no cherry-picking.

---

## 0. The one core idea that fixes everything

Phase 1's mistake was treating **"95% service" as a fixed goal to hit at any cost.** Real optimization inverts this:

> **The service level should be *derived from economics*, not imposed.**

There is a classic result in operations research called the **newsvendor critical ratio**. It says: for a product, the optimal probability of having enough stock is

$$ \text{target service level} = \frac{p}{p + h} $$

where:
- **$p$** = the *cost of running out* (underage cost) = the margin you lose per missed sale = selling price − cost.
- **$h$** = the *cost of having too much* (overage cost) = holding cost per unit per period.

**What this means intuitively:**
- A high-margin fast item (losing a sale hurts a lot) → high service level. Worth stocking up.
- A low-margin slow item (losing a rare sale barely hurts) → low service level. Not worth holding 2 years of cover.

This single formula is what turns us from "a service-level enforcer" into "an optimizer." Instead of a uniform 95%, **every SKU gets its own economically-optimal service level** — and slow-moving items naturally get told to hold less.

**This is the heart of Phase 2.** Everything below supports this idea.

---

## 1. The three workstreams

Phase 1 left three weaknesses, which map to three workstreams. They build on each other in order.

```
A. Better demand (seasonality + proper censoring)
        │  (better signal in)
        ▼
C. Real optimizer (critical ratio + negative-binomial safety stock)
        │  (better rules out)
        ▼
B. Honest evaluation (run candidates, pick best without overfitting)
        │
        ▼
    POSITIVE, DEFENSIBLE NUMBER
```

---

## 2. Workstream A — Seasonality-aware unconstrained demand

### The problem
Today, `src/demand/` imputes a **flat average** for empty-shelf days. That's wrong for seasonal items: winter boots have no demand in summer, so a flat average either over-fills summer gaps or under-fills winter ones. (This is exactly the intuition in the user's question.)

### What we do
Replace "impute the flat in-stock mean" with **"impute the mean × a seasonal index."**

1. **Compute seasonal indices** at the **subcategory × store** level (enough data), per month or per 4-week period:
   $$ \text{index}_m = \frac{\text{demand in period } m}{\text{average demand per period}} $$
   A product with no seasonality has index ≈ 1.0; a winter boot has index ≈ 2–3 in winter, ≈ 0.1 in summer.

2. **Impute censored days** as:
   $$ \text{unconstrained} = (\text{SKU/store in-stock mean}) \times \text{index}_{m} $$
   with the same tiered fallback (SKU-store → SKU-global → subcategory-store → subcategory-global → 0), but now *seasonally scaled* at every tier.

3. **Keep it explainable** — store the seasonal index used per row, so we can always say "we filled this gap using that product's subcategory's winter uplift."

4. **Validate the seasonality is real first** — with 11 months of data we have **one** winter, **one** summer. Compute indices, but be honest that they're estimated from a single cycle. Document this as a caveat.

### Deliverable
`src/demand/` produces a seasonally-corrected `demand.parquet`, plus a `seasonal_indices.parquet` artifact. Re-run Phase 3 forecast on the corrected demand.

### Success criteria
- [ ] Seasonal indices computed and stored per (subcategory, store, period).
- [ ] Imputation is `mean × seasonal_index`, not flat mean.
- [ ] Winter-boot-type subcategories show a **large seasonal swing** (sanity check: the signal is actually there).
- [ ] Uplift stays defensible (not 2× again); document it.
- [ ] Tests green.

---

## 3. Workstream C — The math-backed optimizer

### The problem
Phase 1 used:
- **Uniform 95% service** (should be per-SKU, economics-derived).
- **Normal `z·σ` safety stock** (wrong for lumpy/intermittent demand — the normal distribution assumes smooth daily sales).
- **MOQ=5 for everyone** (economically absurd for a 2.7-unit/yr item).

### What we do

**C1. Per-SKU service level from the critical ratio.**
Replace the fixed 95% with:
$$ \text{SL}_i = \frac{p_i}{p_i + h_i} $$
where $p_i$ = unit margin (selling price − cost), $h_i$ = holding cost (holding rate × cost × lead-time fraction). Cap the result in a sane range (e.g. 50%–99%) so no SKU gets a nonsense 0% or 100%.

> **Expected effect:** slow, low-margin items automatically drop to a low service level (holding less), while fast, high-margin items keep high service. This alone should reverse the "+103% inventory" blowup.

**C2. Correct lead-time-demand distribution: negative binomial.**
For intermittent demand, model lead-time demand as a **negative binomial (NegBin)** — the standard for over-dispersed count data — instead of a normal distribution. Compute the reorder point / base-stock level as the **NegBin quantile** at the target service level:
$$ S_i = F_{\text{NegBin}}^{-1}(\text{SL}_i) $$
The NegBin parameters come from the forecast mean + a dispersion estimate. (Poisson is the special case when variance = mean; NegBin handles variance > mean, which is our reality.)

**C3. Keep an (s, S) / base-stock form, not raw safety-stock.**
- Base-stock level $S_i$ from C2.
- Reorder point $s_i$ = expected lead-time demand, or a periodic-review order-up-to.
- Lot size: EOQ **but only stock items where it makes sense** (see C4), floored at MOQ only for genuinely stocked items.

**C4. Stocking decision (this is where the biggest saving lives).**
A fixed stocking threshold (≈1.5 units/yr) was too low. Introduce an **economic stocking test**: an item is stocked *only if* the expected profit from stocking it exceeds the holding cost of doing so. Slow items that fail the test become **non-stocked** (direct-ship / special-order), not forced to hold 6 units.

> This is the single most important fix: the "+103% inventory" was dominated by stocking thousands of near-dead SKUs. Economically de-stocking them is the big win.

### Deliverable
`src/policy/` rewritten to compute per-SKU service level (critical ratio), NegBin base-stock, and an economic stocking flag. Output `policy.parquet` with `service_level_target`, `base_stock_S`, `reorder_point_s`, `is_stocked`, plus the $p$ and $h$ used.

### Success criteria
- [ ] Service level is **per-SKU**, derived from `p/(p+h)`, never a uniform 95%.
- [ ] Safety stock uses the **NegBin** (or Poisson) distribution, not normal `z·σ`.
- [ ] An economic stocking test exists and a meaningful fraction of SKUs are correctly de-stocked.
- [ ] Average inventory **drops below the €2.45M baseline** while fill rate does not collapse.
- [ ] Every parameter traceable to margin/cost/assumption.

---

## 4. Workstream B — Honest candidate evaluation (the loop)

### The problem
"How do we know our new rule actually wins?" We can't just trust one run. We need a **statistically honest way to compare candidate policies** — like a proper model-selection harness.

### What we do

1. **Define a policy family.** A candidate policy = (service-level derivation, safety-stock distribution, stocking threshold, MOQ, review type). Enumerate a manageable grid, e.g.:
   - Service level: {critical-ratio, fixed 90/95/98}
   - Distribution: {NegBin, Poisson, Normal}
   - Stocking threshold: {0, 0.004, 0.01, economic test}
   - MOQ: {1, 5, EOQ}
   → maybe 3–4 × 3 × 4 × 3 = ~100–150 candidates (prune to a sane set).

2. **Evaluate every candidate with the walk-forward simulator** (reuse Phase 1's `src/simulation/`), each producing the full metric set: avg inventory, fill rate, service level, holding cost, ordering cost, **net TCO**.

3. **Pick the winner honestly — no overfitting.** This is the critical statistical discipline:
   - **Split time:** train/select on the first ~70% of the timeline, **report** on the final ~30% (never seen during selection).
   - The candidate that wins on the selection window is locked in; its **reported number comes only from the held-out window.**
   - This prevents "we tuned until the number looked good" — which is exactly how Phase 1's result fooled us (the tests demanded the answer they wanted).

4. **Report the winner's honest number** — inventory %, fill rate, net TCO — *from the held-out window only*, plus the sensitivity range.

5. **Robustness check:** the winner should be stable — if re-ranking under slightly different assumptions (lead time ±5d, holding ±5%) changes the winner, we report that honestly rather than hiding it.

### Deliverable
`src/optimization/` (new module) with:
- a `PolicyCandidate` dataclass,
- a `run_candidate_grid()` that returns a ranked table of all candidates,
- a leak-free train/select → holdout-report protocol.

### Success criteria
- [ ] Candidate grid defined and enumerated explicitly.
- [ ] Every candidate scored with the *same* metric calculators (apples-to-apples).
- [ ] **Selection window and report window are strictly separated** (no leakage).
- [ ] The final number is reported from the held-out window only.
- [ ] A `policy_comparison.md` artifact ranks all candidates with their metrics.
- [ ] The winning policy beats the observed baseline on **net TCO** on the held-out window.

---

## 5. Order of execution (what to build first)

```
1. Workstream A  →  seasonality-aware demand (fixes the signal)
2. Workstream C  →  critical-ratio + NegBin + economic stocking (fixes the rules)
3. Workstream B  →  candidate grid + leak-free selection (proves which wins)
4. Final number →  positive, defensible, held-out-window-reported
```

**Why this order:** A feeds C (better demand → better base-stock), and B wraps both in an honest evaluation. Don't build B's harness until A and C exist, because the harness needs real candidate policies to compare.

---

## 6. Research grounding (what we're basing this on)

Phase 2 is not invented from scratch — these are established OR/forecasting results:

1. **Newsvendor critical ratio** (`p/(p+h)`) is the canonical result for deriving the optimal service level from economics — the textbook fix for "stop chasing a fixed service level."
2. **Negative binomial lead-time demand** is the standard recommendation for intermittent/spare-parts demand (over-dispersed counts) — multiple papers (Unlu & Rossetti; MDPI 2025; arXiv 2023) confirm NegBin outperforms Normal for lumpy demand.
3. **Croston/TSB family + SBA** remain the practical forecast baselines (Boylan & Syntetos are the field's reference); the point is to *evaluate by inventory cost*, not raw forecast error.
4. **Base-stock policy is optimal** for pure inventory control under a dynamic-programming formulation (standard result); the critical ratio gives the base-stock level analytically.
5. **Forecast-by-inventory-cost selection** (e.g. "sSPEC"/"MCOST" ideas) — the principle that we should pick the forecast/policy that minimises *cost*, not the one with the lowest forecast error — directly motivates Workstream B.

---

## 7. Scope discipline (what NOT to do in Phase 2)

- ❌ Do **not** rebuild the pipeline (data/demand/forecast/simulation machines work).
- ❌ Do **not** add deep-ML (LightGBM/Tweedie) yet — NegBin + Croston is the right level first.
- ❌ Do **not** start the Store-Allocation or Markdown modules — those are later roadmap items and consume the *output* of this phase.
- ❌ Do **not** build any frontend — still not the time.
- ❌ Do **not** tune parameters until the number looks good and then report that number — that's overfitting, and it's what we must guard against with Workstream B.
- ✅ **Do:** keep every number traceable, every assumption labelled, every candidate ranked honestly.

---

## 8. Definition of "done" for Phase 2

Phase 2 is complete when, **from the held-out evaluation window only**:

1. The optimized policy reduces average inventory capital **below the €2.45M baseline**.
2. Fill rate does **not** collapse (no trading sales away for cheap-looking inventory).
3. **Net TCO** (holding + ordering) is **lower** than baseline.
4. The result is reported as a **range across assumptions**, with the winner's stability documented.
5. All workstreams have passing tests and artifacts.

Then — and only then — do we have the honest, positive "X% less capital" sentence we can put on the website.
