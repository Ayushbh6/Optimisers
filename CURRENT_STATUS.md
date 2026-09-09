# CURRENT_STATUS.md — Where the Project Stands

> **Last updated:** 2026-09-09
> **Purpose:** One honest, plain-language record of everything built so far, what it proves, and what's next. Read this before touching any code.

---

## 1. What we set out to build

A tool that turns messy retail data (sales + inventory) into a defensible answer to *"how much stock should this store hold, and when should it reorder"* — proven by replaying the business's own history and showing the € impact.

The product is a **decision + a receipt**:

> "We replayed your last 11 months through our rules, and you'd hold ~X% less cash in inventory while selling at the same rate."

*(The "X%" is aspirational — the real number comes out of the work.)*

---

## 2. What we built (Phase 1 — the Engine)

A complete, working, tested Python pipeline, built end-to-end across the **entire** dataset (2,326 products × 40 stores = 60,968 product-store pairs, 328 days).

### The 5 machines

| # | Module | What it does | Output |
|---|---|---|---|
| 1 | `src/data/` | Turns messy date-window inventory records into a clean daily "units on shelf" table | `daily_onhand.parquet` |
| 2 | `src/demand/` | Estimates hidden demand on days the shelf was empty (lost sales) | `demand.parquet` |
| 3 | `src/forecast/` | Forecasts future demand at category level, splits down to products (Croston/TSB) | `forecast.parquet` |
| 4 | `src/policy/` | Turns forecasts into reorder rules (reorder point `s`, order-up-to `S`) | `policy.parquet` |
| 5 | `src/simulation/` | Replays 11 months with our rules vs actual history, scores the € difference | `simulation_report.md` |

**Tests:** 33/33 passing. Anti-leakage (no peeking at the future) enforced and verified.

---

## 3. What we learned (the honest result)

The engine is correct and trustworthy. But it told us something uncomfortable and **true**:

> The naive reorder rule (always stock, chase 95% service, MOQ=5) is **worse** than what this business already does.

| Metric | Observed business | Our naive rule |
|---|---|---|
| Average inventory | €2.45M | **€4.97M** (+103%) |
| Unit fill rate | 93.6% | **83.9%** (−9.7 pts) |
| Net cost (holding + ordering) | €1.09M | **€1.38M** (+€284K) |

**Why:** the median stocked SKU sells ~2.7 units/year, but our rule tells it to hold 6 units ≈ 2 years of cover. A fixed 95%-service rule with normal-distribution safety stock is the *wrong tool* for extremely intermittent demand.

**What this means:** the pipeline (measuring machine) works perfectly. The *optimizer* (the smart rules in machine 4) is still the beginner version. We have not yet done the actual optimization.

---

## 4. The 5 verified facts that matter for next steps

1. **Pipeline correctness is proven** — baseline reproduction matches the audit within **1.81%**.
2. **Demand uplift is sane now** — 12.23% (was 101% before the censoring fix).
3. **Service level is measured honestly** — one metric on both sides.
4. **The rule currently "enforces" 95% service, it doesn't "optimize"** — it spends whatever it takes.
5. **The levers to fix this are known** — they're the subject of `PLAN_phase_2.md`.

---

## 5. What's next (Phase 2 — the actual optimization)

Replace the beginner rules with real cost-minimising policies. Three workstreams, in `PLAN_phase_2.md`:

1. **Seasonality-aware unconstrained demand** — stop imputing a flat average; respect winter-boots-in-summer type patterns.
2. **Candidate policy loop** — run multiple candidate reorder rules through the simulator and pick the best by honest, unbiased evaluation.
3. **Math-backed optimization** — newsvendor critical ratio, base-stock policy, negative-binomial safety stock (the correct math for intermittent demand).

The goal of Phase 2: produce a **positive, defensible** "X% less capital" number — the thing we can actually show on the website.

---

## 6. File map (where everything lives)

```
PLAN.md                  → Phase 1 plan (engine) — COMPLETE, now historical
PLAN_phase_2.md          → Phase 2 plan (optimization) — THE ACTIVE PLAN
CURRENT_STATUS.md        → this file
docs/OPTIMISER_LOGIC.md  → plain-language "why" notes
docs/archive/plan_phase_1.md → archived copy of the Phase 1 plan
src/                     → the engine (data, demand, forecast, policy, simulation)
tests/                   → 33 passing tests
artifacts/               → intermediate + final outputs
audit/                   → the original data due-diligence work
```

---

## 7. Bottom line (for us, not for clients)

We built the measurement machine. It's correct, honest, and tested. It proved our starting rules are too crude to beat a real business — which is the normal, boring, correct starting point of every optimization project.

**The remaining work is the optimization itself** — turning machine 4 from "enforce 95% service" into "minimise total cost." That's `PLAN_phase_2.md`, and it's where the positive number comes from.
