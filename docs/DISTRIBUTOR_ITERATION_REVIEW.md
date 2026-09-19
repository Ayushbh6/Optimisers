# Distributor iteration review

Status: end-to-end goal active. Two development batches complete; neither establishes enough decision value. Order-size/timing representation is the next investigation. No fresh evaluation or public-product sign-off.

## Confirmed implementation defect

Saved v1 decisions show 13 of 30 known evaluation cases first changed purchases while reporting the stock-cover fallback. Both methods had identical purchases and external events before that first difference. The intended fallback therefore was not the same comparison rule.

The planner computes its baseline inside a projection containing estimated future demand. The comparison's priority calculation treated those estimates as actual booked commitments. A nested projection could also generate another fractional forecast remainder. This means merely preparing the forecast rows could change purchasing priority.

A two-product hand example makes the error visible: €19 available including a €1 supplier charge, six units of P in stock, a real request for 12 P, and forecast demand for P and Q. Both products cost €1 per unit in cases of six. The direct comparison bought 18 P. With forecast rows already expanded, the old fallback instead bought 18 Q. The corrected code buys 18 P in both representations.

A separate fractional-demand check used 0.7 units per weekday. The old direct rule ordered six units; its nested form ordered twelve. The corrected forms both ordered six.

The correction reuses existing forecast cohorts and reserves booked-order priority for real requests. Each fallback in evaluation is now checked against the direct comparison at that same operational state. A disagreement fails the run rather than being hidden in a performance report.

## Limits of this diagnosis

This establishes a concrete defect, not the cause of every loss or proof that the revised optimiser beats the comparison. The initial protocol also lists cancelled estimated requests as a possible source of repeated purchasing gaps. A simple hand-check did not reproduce that claim because existing cancellations are already subtracted. Excluding past estimated due dates is a boundary safeguard, not a demonstrated explanation of the v1 losses.

The current tests pass (115 repository tests). The two-product archived-v1 comparison was additionally run as a direct diagnostic and will be retained as an automated regression test at the next batch boundary. Numerical sources and tests must remain unchanged during the active batch.

## Iteration controls

The failed v1 source is archived with verified original hashes. The new runner retains source identity, hypothesis, settings, all 18 development outcomes and database regeneration records. It resumes an interrupted batch only with identical inputs/code. It removes completed task-created database copies after retaining evidence.

Original reserved cases are known regression evidence. New seeds are declared in the protocol but have not been generated. The unchanged business thresholds still apply. The first batch makes no forecast or solver tuning changes: both methods are rerun after correcting the shared comparison path.

Evidence: `artifacts/distributor-demo/iteration-v2/v1-diagnosis.json`, `verification.txt`, `batch-01/contract.json`, and completed `batch-01/cases/` reports.

## Research for a possible next batch

Commercial inventory planning does account for uncertainty in demand and supplier arrivals. [Lokad's inventory documentation](https://www.lokad.com/inventory-optimization/) describes using distributions of possible outcomes to inform replenishment. Its economic objective is not automatically suitable here: this dataset does not establish selling margins or lost-sale costs. [Brunaud and colleagues' inventory-policy paper](https://egon.cheme.cmu.edu/Papers/Brunaud_InventoryPolicies.pdf) discusses safety stock and explicit uncertainty modelling. These sources support investigating uncertainty protection, not a claim that our current method implements their systems or will achieve their results. Checked 15 September 2026.

If the corrected batch still loses service, the next design should use observed request variation to challenge proposed purchases and keep customer-specific commitments visible. It should not merely multiply the forecast until a held-out result looks attractive. This remains a proposed direction pending the corrected batch.

## First corrected-case loss traced

The corrected ordinary-trading development case 1101 lost 12 on-time units of PRD-010. It purchased 36 units on 5 August where the comparison purchased 48, then purchased 60 on 12 August where the comparison purchased 48. Two requests created on 8 and 11 August and due on 12 August account for the lost service. Both saved action histories reproduce the reported outcomes.

Using only the 5 August operational snapshot, removing that case while keeping the comparison's other future purchases fixed did not reduce projected PRD-010 service over the first 14 days under the nominal forecast. It did reduce service by nine units in a higher-demand sensitivity based on the observed historical weekly forecast error. The actual missed orders were not used to set that stress magnitude. This is a diagnostic of one case; it does not reproduce the candidate's entire original future schedule or prove general improvement.

A separate staged sensitivity module now creates lower and higher views by spreading one observed mean absolute weekly error across five weekdays. These are stress magnitudes, not confidence intervals or generator probabilities. It checks both proposals under identical conditions and leaves real bookings unchanged. Seven staged tests cover error handling, no input mutation, demand remainder and identical-plan parity. This module is not loaded into the active first batch.

The proposed second batch will use those views to screen candidate proposals against the same baseline under each view. It will retain the baseline when a proposal gives up service or booked fulfilment in a stress view. No new solver tuning or fresh evaluation is proposed in that batch. Its value remains to be tested across all development cases.

## First batch completed

All 18 development cases completed with zero ledger errors and no fallback-identity failures. Two cases met an individual improvement route: ordinary 2202 and restricted spending 2202. No family showed a consistent improvement across all three development seeds. The largest service decline was 2.76 percentage points in ample stock 2202. This does not justify opening fresh evaluation. Complete outcomes and exact source archive are retained in `batch-01/`.

The demand-sensitivity guard and source-archive/exclusive-lock helpers are now integrated for batch-02. The two archived-v1 hand examples are automated regression tests. The new batch changes the selection guard, not the shared forecast, solver time allowance, comparison safety cover or business recipe. The fresh seeds remain unopened.

## Further findings while batch-02 runs

The stricter default removes the first ordinary-case service losses, but early completed cases mostly retain the baseline. This is preliminary, not a final batch assessment. The solver still proposes quantities using average demand and then checks variation afterwards.

A separate joint-view model prototype now binds the same purchase quantities across nominal/lower/higher demand views. It minimises nominal stock exposure while requiring each view's service and capacity constraints. No probability weights or shortage prices are introduced. Three hand tests verify common decisions, explicit budget infeasibility and required targets. This prototype is staged only; it is not running in batch-02 or accepted as the third candidate.

An additional public-history diagnostic found that 26 of 29 products with projected demand have median projected cohort sizes below half their median recorded positive request size. This follows from representing average demand as small daily cohorts. It is an approximation, not a forecasting bug by itself, but can weaken purchasing decisions for customers who require complete lines. The next candidate review must examine request-size variation rather than relying solely on a higher smooth average. Evidence: `request-size-diagnostic.json`. The diagnostic uses the retained default's last eight historical weeks, not future orders.

Separately, 18 staged validation tests now cover malformed incoming quantities/dates, unknown supplier/product references, overlapping terms, overcapacity, future-record labels, invalid assumptions and unknown exclusions. They retain unknown/overdue arrival dates as visible obligations rather than discarding them. These input checks are not active in the frozen batch-02 source.

The retained receipt history also shows a material gap between observed freshness and the fixed planning assumption. Past receipt-linked lots cover all 30 products; the shortest observed remaining life is 70 days, while product medians range from 71 to 351 days. The approved unknown-incoming assumption remains 60 days. For a customer requiring 60 days remaining, that assumption makes a new lot eligible only on its arrival day. This can affect purchasing decisions substantially. Past observations are not supplier guarantees, and this diagnostic does not authorise silently replacing the 60-day assumption to obtain a better score. Evidence: `historical-freshness-diagnostic.json`, using historical records only.

A fourth hand test demonstrates the order-grouping issue independently of any optimiser score. With 12 units available and whole-line customers, four separate six-unit requests receive 12 on-time units in total; one 24-unit request receives none. Total demand is the same. Treating small daily cohorts as a reliable proxy for complete-line service is therefore unsafe without testing the actual order-size pattern. A joint model using only smooth demand views is not yet a sufficient next-candidate specification.

## Second batch completed

All 18 cases completed with zero accounting errors and no on-time service regressions. **Zero cases met an individual improvement threshold.** Restricted spending improved by 1.32 points (seed 1101) and 1.08 points (2202), below the two-point route; associated stock reductions were also below ten percent. The largest stock reduction was 3.42% in ample stock 2202, with unchanged service. Screening protected service but mostly selected the comparison, so it did not establish the requested commercial improvement. All paired decisions and sensitivity records are retained.

Fresh evaluation remains closed. Before a third full batch, investigate order-size/timing scenarios rather than merely raising a smooth forecast. The joint-view prototype is available for that work, with four hand tests. Stricter operational validation was integrated after the batch; the full repository now passes **146 tests**. It does not change the recorded batch-02 results or remove any cases. Completed database copies and test scratch were removed after retaining evidence.

## Third candidate verification

Historical order-pattern views and the joint model are now integrated. Five pattern tests cover original order size/customer/weekday, declared coverage, future mutation, booking replacement and historical prior bookings. Five joint-model hand checks cover shared purchasing, budget infeasibility, explicit targets and whole-line allocation. The first retained default operational snapshot used no evaluator records; it selected the baseline after physical replay rejected the candidate. Its 11.5-second planning call and solver statuses are retained in `pattern-planning-diagnostic.json`. This is one planning diagnostic, not an eight-week evaluation result.

An unscoped test invocation accidentally collected archived exploratory scripts under artifacts as well as active tests. The old exploratory solver initialised HiGHS with a different process-wide thread setting, causing five solver checks to fail with status 4 rather than a feasible/infeasible answer. The failed log is retained in `v3-verification.txt`. `pytest.ini` now explicitly selects the active `tests/` suite; archived exploration remains unchanged and should run in a separate process. The iteration source identity includes this test configuration. This test-discovery correction is not an optimiser improvement.

The scoped active suite passed **156 tests in 40.38 seconds**. Source hashes are retained in `v3-verification-sources.json`; retained default database/artifact hashes still match. Promoted prototype copies and test scratch were removed. Batch-03 is the full 18-case test of this candidate, after which the protocol requires an explicit progress review.

## Customer and product harm review

A paired breakdown audit of all 36 completed batch-01/batch-02 cases confirmed identical requested quantities for each compared customer and product. Batch-01 has 69 customer/product groups with lower on-time service; batch-02 still has seven despite no aggregate scenario service losses. In restricted spending 2202, customer CUS-014 loses 13 on-time units (11.93 percentage points); restricted spending 1101 includes customer losses of seven and six units. The worst product percentage in batch-02 is PRD-027, six fewer on-time units out of twenty requests (30 points). These are overlapping product/customer views of units, not independent losses to add together. Exact changes are retained in `completed-batch-harm-review.json`.

This finding does not change the predeclared gate, but rules out describing aggregate service protection as protection for every customer. A candidate review must explain who bears a shortage, including small-volume groups. No customer priority or convenient exclusion has been introduced to improve the score.

The existing grouped service reports cover requests created in the eight-week evaluation window. Historical carry-in obligations remain in physical accounting and planning, but require a separate explicit outcome breakdown before final release; they must not disappear from the buyer's risk view. Report that cohort separately rather than silently changing the frozen headline denominator.

## Joint-model dispatch diagnostic while batch-03 runs

A separate operational-only repeat retained the first joint model's purchase schedule and compared its physical dispatch with the baseline under all five public demand views. The time-limited candidate lost 1.27 service points in the nominal view, 1.34 in historical pattern 2 and 3.36 in pattern 3. Other views improved. These are planning projections, not realised future outcomes, and a time-limited repeat can return a different incumbent from the earlier diagnostic. Record: `joint-dispatch-diagnostic.json`.

The losses include both partial and whole-line customers, across 14-, 30- and 60-day freshness requirements. Representing whole-line sizes exactly therefore does not by itself close the model's allocation-versus-physical-dispatch gap. Rejection and baseline fallback are functioning, but the decision model can still spend its solve allowance on proposals that cannot deliver their projected service under the fixed warehouse rules. No running batch source was changed.

If the third batch still lacks useful improvements, the required progress review should assess an exact-dispatch purchasing search rather than another parameter sweep: evaluate dated case-order schedules through the physical rules, then combine choices subject to common supplier baskets, budget and capacity. Any bounded candidate search must retain all 28 planning days, future ordering opportunities and explicit limits on optimality claims. This is a possible modelling correction, not a selected fourth batch or evidence of value. Await the full third-batch results first.

## Simulation-based discrete purchasing trial

After batch-03 completed with zero qualifying improvements, the exact-dispatch path was implemented. It starts from the stock-cover schedule, edits only today's integer-case supplier basket, retains later baseline order opportunities, and physically replays every feasible candidate under nominal/lower/higher demand and four historical request patterns. Explicit limits are eight basket lines, one-case steps, eight two-line candidates and forty total candidates. No shortage price, margin or weighted value score is used.

Three hand tests establish candidate generation, minimum repair and exact predicted-versus-replayed selection. The active suite passes 165 tests. The earlier 4 June Honey Drops/Lentil Soup result is reproduced in 0.89 seconds using 42 physical replays.

A four-case repeated-decision test was frozen before outcomes using seed 1101 for ordinary, restricted spending, supplier disruption and ample stock. Average stock plus commitments fell 9.27%, 3.03%, 11.69% and 8.35% respectively. The first three cases had no customer/product delivery regression. The ample-stock control lost two on-time and total PRD-004 units for CUS-016, a 0.08-point aggregate service decline; its complete-line service fell 0.34 points. This is a negative safety result even though investment fell.

The 18-case batch is therefore not authorised. Diagnose the 31 July PRD-004 reduction in a bounded way before any wider run. Fresh seeds 91301–91305 remain unopened. Full evidence: `docs/DISTRIBUTOR_DISCRETE_TRIAL_01.md` and `artifacts/distributor-demo/discrete-physical-trial-01/`.

## Discrete-trial regression diagnosis

The two-unit ample-stock loss is caused entirely by the 31 July reduction of Mint Drops from 54 to 48 units. It is not a dispatch, freshness, expiry or capacity error. The search replays each candidate against fixed future stock-cover purchases, so it does not model how today's edit changes later baskets and weekly-budget competition.

When future stock-cover decisions are recalculated from each candidate's evolving state, the existing higher-demand view rejects this edit: six extra Mint Drops on 7 August crowd a 24-unit Corn Bites minimum out of that week's budget, delay its receipt by seven days and make a four-unit line late. The correction is therefore adaptive future policy replay, not another demand multiplier or parameter sweep. Production logic was not changed during diagnosis. The 18-case batch and fresh evaluation remain closed. Full evidence: `docs/DISTRIBUTOR_DISCRETE_DIAGNOSIS_01.md` and `artifacts/distributor-demo/discrete-physical-diagnosis-01/`.

## Adaptive discrete trial

The correction is implemented: every candidate commits only today's basket, then recalculates stock cover from its own physical state under each of the seven required views. Five hand tests include exact replay equality and the diagnosed cross-product budget displacement. The active suite passes 167 tests, and the original 31 July Mint Drops edit is now rejected.

A new four-case contract was frozen before outcomes. Ordinary trading, restricted spending and supplier disruption preserved aggregate and customer/product delivery results while reducing simulated average investment by 8.31%, 0.08% and 8.20%. Ample stock reduced investment by 8.23% but lost 12 on-time Nougat Bar units for `CUS-015` (-0.48 service points); all 12 shipped one workday late. The policy had skipped both 10 and 17 July 12-unit orders. Restoring either €66.12 order protects the line, so those counterfactuals are overlapping rather than additive.

This is a new demand-pattern coverage failure, not the fixed-future-policy defect and not a physical-dispatch mismatch. The release gate remains failed. No 18-case batch, fresh seed or website work is authorised. Full evidence: `docs/DISTRIBUTOR_ADAPTIVE_DISCRETE_TRIAL_02.md` and `artifacts/distributor-demo/discrete-physical-trial-02/`.
