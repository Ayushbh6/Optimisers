# Phase 1 — Completed pipeline repair plan

> Completed and signed off on 11 September 2026, under the recorded-purchase replay assumptions below. Part 2 has not started.

This is the live completion record for the approved **Part 1 — Repair and Verify the Existing Pipeline** plan. Checked items record the final reviewed implementation. The [original Phase 1 plan](archive/plan_phase_1.md) remains frozen as a historical record, as required by REPO_RULES.md.

## Final acceptance

- **54 tests passed**; all **27 full-data sensitivity settings** completed and were verified.
- The full rebuild reconciles **124,542 purchased units** and **7,547 returned units**, with **zero stock-balance errors**.
- An independent raw-to-report repeat produced byte-identical copies of all **11 numerical Parquet outputs** common to both runs.
- The replay fulfils **97.18%** of eligible recorded purchases. Ending stock is **283,392 units**, with **2,565 units** still on order.
- Identified future-peeking paths are removed from the accepted build and stage wrappers. Dated inputs and the shop's restricted learning interface enforce the boundary; future-data mutation tests check that later changes leave earlier estimates, forecasts and orders unchanged.
- This does not establish a savings claim: simulated stock value is higher on the matched scope, some purchases are unfulfilled, and historical ordering costs are unavailable.

See [CURRENT_STATUS.md](../CURRENT_STATUS.md) for the latest results and run records, and [PART1_FINAL_REVIEW.md](PART1_FINAL_REVIEW.md) for the requirement-by-requirement review. Acceptance covers the shared `src.build_part1` pipeline and its stage wrappers; older internal helpers outside that path are not an alternative accepted pipeline.

---

# Part 1 — Repair and Verify the Existing Pipeline

## 1. Goal and agreed boundaries

**Goal:** make the existing pipeline produce reproducible, traceable results without future information, hidden data assumptions or unfair comparisons.

```text
Raw records
→ separate facts from estimates
→ forecast using information available at the time
→ replay recorded purchases
→ report stock held, purchases fulfilled and remaining uncertainty
```

The agreed scope is:

- **Full dataset:** repair shared logic, test small cases first, then rebuild all products and stores.
- **Recorded purchases first:** repair lost-demand estimates for forecasting, but do not treat estimated missed customers as observed replay demand.
- **Learning from its own results:** after initial historical training, the simulated shop learns from its own fulfilled purchases and stock availability.
- **Explicit limits:** missing business facts may leave some financial comparisons unavailable.
- **Existing methods:** retain the current rare-sales forecasting methods and reorder policy. Better policies, seasonality, candidate selection and uncertain-demand trials belong to Part 2.
- **Execution:** initial implementation used the agreed delegation. The user subsequently required the final review and remaining fixes to be completed directly, without further subagents or handovers.

Success means the machinery is correct under its stated assumptions. It does **not** require better forecasts, lower inventory or positive savings.

## 2. Tasklist A — Repair the data and forecasts

### A1. Establish one reproducible run contract

- [x] Centralise shared dates, paths and assumptions so individual stages cannot silently use different settings.
- [x] Reconstruct the complete **1 June 2025–24 April 2026** dataset.
- [x] Use **1 June–15 January** for initial learning and **16 January–24 April** for the daily replay. These are development evaluation dates, not a claim of previously untouched data.
- [x] Add one end-to-end command with a configurable output directory. Existing stage commands become thin wrappers around the same functions.
- [x] Record input hashes, code revision, configuration, schema version and stage dependencies in a run manifest.
- [x] Pin the missing Parquet and test dependencies using the versions verified in the existing environment: PyArrow 25.0.1 and pytest 9.1.1.
- [x] Reject old or mismatched artifacts instead of silently mixing them with repaired outputs.

**Completion check:** a run can be traced back to its exact inputs and settings without relying on existing generated files.

### A2. Separate sales, returns and stock evidence

- [x] Keep gross purchases and returned units in separate columns. Check that return flags and quantity signs agree.
- [x] Use purchases for demand; use purchases minus returns only for physical stock movement.
- [x] Include every product-store pair appearing in either ledger. Retain purchases before the first inventory record rather than losing them during joins.
- [x] Treat inventory snapshots as **closing stock**, supported by the observed same-day relationship between sales and stock changes.
- [x] Preserve original negative stock and accounting values alongside any physical-stock normalisation.
- [x] Fill costs, prices and product metadata only within the same product-store pair, using information already available. Remove future backfills, cross-product fills and the arbitrary missing-cost substitute.

**Completion check:** raw purchase and return totals reconcile exactly; unexplained stock differences remain visible.

### A3. Separate the historical reference from the stock estimate available at the time

Produce two explicitly labelled views:

| View | Purpose |
|---|---|
| **Historical reference** | Expand the recorded intervals for retrospective accounting. Uncovered dates remain unknown. |
| **Causal stock estimate** | Process snapshots and transactions in date order, using only information available by that day. |

- [x] Keep retrospective interval endings out of forecasting and policy inputs.
- [x] On a snapshot date, accept the reported closing quantity without subtracting that day’s sales again.
- [x] Between snapshots, carry the previous estimated close forward through purchases and returns. Mark this as estimated.
- [x] If purchases exceed the estimated available stock, record the unexplained shortfall before flooring the physical estimate to zero.
- [x] At the next snapshot, record the adjustment between estimated and reported stock. Do not automatically call it a delivery.
- [x] Remove all rules using the final observed date to invent retirement or zero stock.
- [x] Do not let a later snapshot change an earlier estimate. “Interior gap” versus “final tail” may be retrospective report labels only.
- [x] Before any usable stock anchor exists, keep stock unknown.

**Completion check:** changing future records cannot change an earlier causal stock estimate.

### A4. Repair the demand estimator

- [x] Remove future lifecycle information and full-history demand-rate fitting.
- [x] Estimate each day’s missing demand using rates learned through the previous day; keep the existing fallback order and seven-day minimum exposure settings.
- [x] Count only days assessed as available for the demand-rate denominator. Exclude unknown stock, depletion/partial-availability days and unresolved stock discrepancies.
- [x] Allow forward-estimated availability under the documented stock-flow assumption, while separately reporting how much donor exposure was estimated.
- [x] On a possible stockout day, keep the demand estimate at least as large as recorded purchases. With no usable prior rate, retain purchases and flag insufficient evidence.
- [x] Store the availability assessment, estimate, fallback used and information cutoff.
- [x] Call the output **estimated demand**, never verified “true demand”.

**Completion check:** returns cannot depress purchase demand; unknown or empty-shelf days cannot silently dilute an in-stock sales rate.

### A5. Repair daily forecasting and its evaluation

- [x] Rebuild forecasts daily from the available history. Initial replay forecasts use information through 15 January; subsequent forecasts use the simulated shop’s own history.
- [x] Restrict product lists, category pooling, sales shares and costs to information available at each cutoff.
- [x] Correct Croston’s interval counting and TSB’s initialisation/residual calculation using hand-checkable examples. Retain Croston as the default and the existing smoothing settings.
- [x] Correct weekly grouping to **Monday–Sunday**. Exclude incomplete weeks from weekly model fitting; retain their transactions for daily history and share updates.
- [x] Make daily, weekly and four-week output units explicit and consistent.
- [x] Label existing uncertainty bounds as an approximation. Report measured coverage where evaluation is possible; do not promise calibrated 95% coverage.
- [x] Compare forecasting with last-completed-week and historical-average baselines using the same dates and targets.
- [x] Report error against observed purchases separately from error against estimated demand. Undefined comparisons remain unavailable.
- [x] Replace “forecast must win” tests with correctness tests.

**Completion check:** each forecast explains what history it used, what period it predicts and how its benchmark was calculated.

## 3. Tasklist B — Repair the replay and comparisons

### B1. Give the replay a clear information boundary

The purchase stream belongs to the replay controller. The forecaster receives only the simulated shop’s observable history.

```text
Recorded purchases arrive
→ available stock determines fulfilled purchases
→ only fulfilled purchases and stock availability enter the shop’s history
→ its next forecast and order are calculated
```

- [x] Prevent the forecaster from reading unfulfilled purchase targets or later historical sales.
- [x] Reuse the repaired demand estimator on the simulated shop’s own history.
- [x] Give each sensitivity run independent forecasting state after initial learning.
- [x] Keep historical forecast benchmarking separate from this simulated feedback loop.

### B2. Make every stock movement explicit

Use this daily sequence:

```text
Opening stock
→ scheduled order arrivals
→ recorded purchases and fulfilment
→ returned stock
→ closing stock
→ forecast and order for future days
```

- [x] Initialise existing pairs from their causal closing-stock estimate on 15 January.
- [x] Initialise pending orders as empty, explicitly labelled because historical open orders are unavailable.
- [x] For a pair without usable starting stock, begin its comparison on the day after its first usable closing snapshot. Record excluded earlier purchases.
- [x] Treat that snapshot as starting inventory once; never cap it to the policy target or inject later historical receipts into the simulated shop.
- [x] Apply historical returns at day-end as an explicitly assumed external return stream. Do not infer return links to simulated sales.
- [x] Keep all physical stock, purchases, orders and arrivals in whole units.
- [x] Enforce the configured minimum order quantity on actual orders. Do not remove excess stock when the target falls.
- [x] Receive orders after the configured calendar-day delay. Preserve outstanding orders and remaining stock at the replay’s end.
- [x] Never stop replenishment using a future retirement date.

**Completion check:** opening stock plus receipts and returns, minus fulfilled purchases, equals closing stock for every simulated pair-day.

### B3. Preserve the existing policy while correcting its execution

- [x] Keep the present default policy settings: ten-day lead time, 95% nominal target, 20% annual holding rate, MOQ five and the existing stocking threshold.
- [x] Use one shared policy calculation for standalone output and replay.
- [x] Use the latest valid pair-specific cost available at the decision time. If none exists, flag the policy as unavailable and place no new order until a usable cost arrives.
- [x] Record stocking eligibility, cost assumptions and reasons for unavailable recommendations.
- [x] Retain the existing policy’s approximations as labelled limitations; do not introduce economic stocking decisions or new stock-buffer distributions.

### B4. Replace misleading metrics and accounting

- [x] Make **observed-purchase coverage** the main service-related metric: fulfilled recorded purchases divided by recorded purchases.
- [x] State that the historical reference is 100% by construction. This is not its true customer fill rate.
- [x] Include products the policy chooses not to stock in the comparison denominator.
- [x] Report coverage, unfulfilled units, closing inventory, remaining stock and orders together, with breakdowns by division and store.
- [x] Value both sides using the same dated cost series and comparable product-day scope.
- [x] Report reference-stock and cost coverage. Where reference quantities or costs are missing, show matched-scope results; do not label partial totals as full-chain capital.
- [x] Remove the hardcoded historical delivery count. Historical ordering cost and total-cost savings remain unavailable without defensible order records.
- [x] Report simulated ordering cost separately using the existing assumed store-day batch charge and per-line charge, including both components.
- [x] Retain the existing 27 sensitivity settings. Recalculate comparable baseline holding cost at each scenario’s rate.
- [x] Label costs for the actual evaluation period. Show capital tied up separately from operating costs.
- [x] Show the first 15 replay days separately because unknown opening orders affect startup. Use the same dates on both sides.
- [x] Suppress any “same sales” interpretation when observed-purchase coverage falls.

**Completion check:** every comparison uses the same scope, timing, valuation and definitions.

## 4. Interfaces and tests

Keep the existing module boundaries. Add small shared contracts rather than a new framework:

- **Run configuration:** input/output locations, dates and assumptions.
- **Forecast snapshot:** product-store, information cutoff, forecast start, units, method, uncertainty label and source-history details.
- **Replay state:** the shop’s inventory, pending orders and observable history.
- **Replay ledger:** daily movements, fulfilment, decisions and valuation.
- **Run manifest:** input/configuration identity, artifact dependencies, coverage and limitations.

The historical reference and future purchase stream must not be accessible through the forecast/policy contracts.

Required tests:

- [x] Future-data mutation: changing later sales, returns, prices, products or interval endings leaves earlier estimates, forecasts and orders unchanged.
- [x] Feedback isolation: an unfulfilled purchase target cannot enter the next forecast as an observed sale.
- [x] Closing-stock timing, same-day sales and returns, missing intervals, negative stock, unexplained shortages and unknown starting stock.
- [x] Pair-local cost handling; no future or cross-pair substitution.
- [x] Forecast initialisation, long zero runs, weekly boundaries, horizon units and independent aggregate-to-product reconciliation.
- [x] Exact order delays, minimum quantities, overlapping orders, target reductions and end-of-window outstanding orders.
- [x] Whole-unit stock conservation and identical comparison denominators.
- [x] Missing historical order data prevents a total-cost savings claim.
- [x] Sensitivity accounting applies the same rate to both sides.
- [x] A small end-to-end test builds from raw fixtures into an empty temporary directory.
- [x] A full-data acceptance run rebuilds every stage without reading legacy outputs.

Tests must detect the known defects before their fixes. None may demand a favourable business result.

## 5. Completion and handover

Implement the tasklists in order, with the orchestrator reviewing each completed stage before downstream integration.

Part 1 is complete when:

- The full raw-to-report build succeeds and meaningful tests pass.
- Identical inputs and settings reproduce the same numerical outputs.
- Every source transaction is retained or explicitly accounted for.
- The report separates observed facts, reconstructed estimates and unavailable information.
- Daily decision traces prove that the shop uses only information it could observe.
- Live documentation replaces stale confidence and savings claims with the verified result.
- The frozen archived plan and the user’s existing repository rules remain untouched.
- The handover states remaining Part 2 prerequisites: better policies, realistic missed-demand trials, unresolved operational assumptions and independent validation before a website savings claim.

**The deliverable is a trustworthy recorded-purchase replay and a repaired forecasting pipeline—not yet the final commercial savings claim.**
