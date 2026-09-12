# Current status

> Final Part 1 sign-off: 11 September 2026.

**Part 1 is complete under the agreed recorded-purchase replay assumptions.** The final review repaired the remaining integration gaps, verified the saved records independently, and checked all 27 full-data sensitivity settings. This replaces the earlier partial main-run acceptance.

The result is a measuring system we can inspect and reproduce. It is not yet evidence that our policy saves the retailer money.

## Verified evidence

- **54 tests pass**, including future-data changes, feedback isolation, later starting-stock anchors, model calculations, daily shares, dated costs, order timing, matched accounting and raw-fixture rebuilds.
- A clean build reconstructed **14,635,042 stock rows** and the same number of demand rows from the raw files.
- All **125,751 source transaction rows** reconcile: **124,542 purchased units − 7,547 returned units = 116,995 net units**.
- The replay contains **6,151,308 rows**. Independently recalculating stock movements found **zero stock-balance errors**. Arrivals match orders placed the configured number of calendar days earlier.
- The ending-stock breakdown equals the pair-level ledger: **283,392 units**. Another **2,565 ordered units** remain outstanding, with exact due dates retained.
- **All 27 full-data sensitivity settings completed** with independent shop learning after initial training. Their reference holding costs use the same rate and scope as their simulated side. The default setting reproduces the main run.
- A separate raw-to-report rebuild produced **byte-identical copies of all 11 numerical Parquet outputs** common to the two runs. Input, artifact and implementation hashes were independently checked.
- The frozen archive has no tracked changes. `docs/REPO_RULES.md` matches its pre-review hash.

The completed checklist is in [the live Phase 1 plan](docs/plan_phase_1.md); detailed review evidence is in [the final review](docs/PART1_FINAL_REVIEW.md).

## Completion against the original plan

| Requirement | Status | What establishes completion |
|---|---|---|
| A1 — Shared run contract | Verified | Shared dates and assumptions, fresh output directories, schema v2, exact input/source hashes, pinned dependencies, stage dependencies, thin stage wrappers and reproducible numerical outputs. Changed inputs or implementation invalidate a running build. |
| A2 — Facts and stock movement | Verified | Separate purchases/returns, strict quantity and flag validation, preserved raw accounting values, all ledger pairs, purchases before stock anchors, and dated pair-local cost/price/metadata handling. |
| A3 — Causal stock | Verified | Closing snapshots anchor stock once; interval endings affect only the historical reference. Shortfalls and adjustments remain visible. Future mutation tests protect earlier estimates. |
| A4 — Estimated demand | Verified | One shared learner uses prior-day rates, seven-day donor exposure and explicit fallback/cutoff records. Unknown, depleted and discrepant days do not dilute available-day rates. Estimated exposure is recorded separately. |
| A5 — Forecasts and evaluation | Verified | Daily shares and dated product facts; complete Monday–Sunday model weeks; daily, weekly and four-week units; hand-checked Croston/TSB behaviour; separate observed/estimated target errors and equal-scope baselines. Uncertainty remains explicitly approximate. |
| B1 — Shop learning boundary | Verified | The shop receives fulfilled purchases and shelf evidence, never unfulfilled purchase targets. Its own demand estimates feed its next forecast. Changing hidden targets cannot change the forecast when observable history stays the same. |
| B2 — Physical replay | Verified | Whole-unit movements, later anchors activated the next day, external day-end returns, exact delays, MOQ, no stock disposal when targets fall, and outstanding orders retained. |
| B3 — Existing policy | Verified | Existing settings retained; orders fill the gap to the order-up-to target. Missing costs block orders. Every eligible pair-day has an explanation, including unavailable forecasts/costs and no-order decisions. |
| B4 — Fair comparisons | Verified | Identical dated costs and matched pair-days on both sides; corrected store-day batching and ending-stock totals; first 15 days and remainder separated; all 27 full-data settings verified. Historical order cost and total savings remain unavailable. |

## What the corrected result says

The evaluation is **16 January–24 April 2026**, after initial learning from **1 June 2025–15 January 2026**. These are development evaluation dates, not a previously untouched holdout.

| Main-run measure | Verified result |
|---|---:|
| Eligible recorded purchases | 33,434 units |
| Fulfilled purchases | 32,492 units |
| Unfulfilled purchases | 942 units |
| Observed-purchase coverage | **97.18%** |
| Earlier purchases excluded before usable stock anchors | 378 units |
| Ending simulated stock | 283,392 units |
| Outstanding orders | 2,565 units |
| Simulated ordering cost for the 99-day period | €227,932 |
| Store-day batch component | €151,050: 3,021 batches at €50 |
| Order-line component | €76,882: 38,441 lines at €2 |

The historical reference has 100% recorded-purchase coverage by construction. This is not a true customer fill rate. Because simulated coverage is below 100%, this result cannot be described as “the same sales”.

On the **same matched quantity/cost scope**, average stock value is **€2.50 million for the reference** and **€4.49 million for the simulation**. Holding costs for the actual 99-day period are approximately **€135,727** and **€243,382**, respectively. These are **partial matched-scope values, not full-chain capital**: 2,849,918 of 5,890,360 eligible pair-days have both reference quantities and usable common costs.

Croston also performs worse than the last-completed-week baseline on the observed-purchase evaluation. No favourable forecast or business result was required by the tests.

**There is no savings claim.** Historical ordering costs remain unknown, so total-cost savings cannot be calculated. The current policy holds more stock on the matched scope and misses some recorded purchases.

## Assumptions that remain important

- Historical closing snapshots and forward stock flow are imperfect evidence of shelf availability. Of 9,355,275 assessed historical donor days, **9,131,846 (97.6%)** use forward-estimated stock. Estimated demand is not verified missed-customer demand.
- Starting historical open orders are unknown and therefore assumed empty. The first 15 replay days are reported separately on the same comparison dates.
- Historical returns enter at day-end as an assumed external stock stream. They are not linked to simulated purchases.
- Lead times, MOQ, stocking threshold, holding rates and order charges are assumptions. Missing historical order records prevent a total-cost comparison.
- The uncertainty bounds are a normal approximation, with an explicit independent-day scaling assumption. Measured coverage is not a calibrated 95% promise.

## Run records and repeat command

- Retained lean accepted evidence and Phase 2 inputs, including all sensitivity settings: `artifacts/part1-final/`.
- Final audits and test evidence: `artifacts/part1-final/verification/`.
- Cleanup inventory: `artifacts/part1-final/cleanup_record.json`.

The accepted run is now stored inside this repository. Its 14 artifact hashes were checked before and after the move. Superseded temporary runs and the independent repeat were deleted after verification; their final audit evidence is retained. After sign-off, three large reproducible detail tables were also removed because the bounded Phase 2 work does not need them: `forecast.parquet`, `policy.parquet` and `forecast_benchmark_detail.parquet`. Their verified hashes remain in the manifests. Future run outputs should stay inside this repository and superseded outputs should be removed after verification.

The source and command below recreate the results into a fresh repository-local output directory:

```text
python -m src.build_part1 --output-dir artifacts/part1-next --sensitivity
```

The lean retained set contains `run_manifest.json`, `acceptance_checks.json`, daily stock and demand data, the replay ledger, compact forecast benchmarks, matched comparisons, pending orders, exclusions, breakdowns and `sensitivity.parquet`.

## Direction for Part 2

The dataset source is confirmed as Jimmy Smith's *Retail Transactions and Stocks Data*, Mendeley Data version 1, DOI `10.17632/27x8mjm8k4.1`, published under CC BY 4.0. Its published description and defining counts match the local sample. Public attribution must describe it as a published/anonymised retail-business dataset, not a named client engagement.

Part 2 now begins with the bounded feasibility check in [PLAN_phase_2.md](PLAN_phase_2.md). The plan was locked on 12 September 2026 with a 90-minute feasibility limit, fixed opportunity-ranking rules, explicit website screening thresholds and a maximum of six experiment executions. It has not run. The first task is to rank the optimisation problems this dataset can honestly support—store stocking/replenishment, forecast selection, cross-store allocation, and slow-stock/markdown prioritisation—then test only the strongest opportunity. This dataset does not need to prove every future website claim; another verified dataset may support a different demo. Full implementation waits for that decision.
