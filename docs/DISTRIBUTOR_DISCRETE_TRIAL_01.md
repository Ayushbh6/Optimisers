# Simulation-based discrete purchasing — bounded trial 01

Synthetic development evidence, not client savings. Completed 16 September 2026. The 18-case batch and fresh seeds 91301–91305 remain unopened.

## Goal and rule

Goal: can exact supplier-basket optimisation reduce stock investment while protecting the deliveries the buyer already achieves?

Stock-cover basket → bounded whole-case edits → commercial preflight → exact warehouse replay in seven demand views → reject harm → choose the lowest-average-investment survivor.

The planner no longer uses the relaxed allocation model to choose its recommendation. It changes only today's basket and keeps all later stock-cover ordering opportunities in the 28-day plan. Candidate edits are removals, one-case reductions/increases, minimum-order replacement top-ups using products already in the basket, and at most eight deterministic two-line edits. The hard cap is 40 candidates across at most eight basket lines.

Every feasible candidate is physically replayed under nominal, lower and higher demand plus four fixed historical order patterns. It is rejected for a line-level delivery loss, lower booked fulfilment, lower service, higher expiry or higher terminal stock plus commitments in any required view. No margins, shortage penalties, evaluator outcomes or weighted business score are used.

## Correctness checks

- Three new hand tests cover deterministic candidate bounds, supplier-minimum repair and exact physical selection.
- The selected hand candidate's saved metrics equal a separate physical replay exactly.
- The active repository suite passes **165 tests**.
- On the 4 June operational snapshot, the implementation reproduces the earlier lead: remove 96 Honey Drops and increase Lentil Soup from 18 to 48 units. Cash required is €270.72. One of five feasible baskets survives 42 replays; search time is 0.89 seconds on this machine.

## Frozen repeated-decision test

Before generating outcomes, `contract.json` fixed seed 1101—the first declared development seed—for ordinary trading, restricted spending, supplier disruption and ample stock. Both policies started from identical immutable records and then evolved independently for eight weeks. Each committed only its own current-day decision. Generated database scratch was removed after each compact case report was saved.

| Case | Service change | Average stock + commitments | Expiry change | Ending stock + commitments | Changed decisions | Customer/product regressions |
|---|---:|---:|---:|---:|---:|---:|
| Ordinary | 0.00 points | -9.27% (-€718.24) | €0.00 | -€1,180.26 | 9/32 | 0 / 0 |
| Restricted spending | +0.80 points | -3.03% (-€124.39) | €0.00 | -€228.30 | 2/32 | 0 / 0 |
| Supplier disruption | 0.00 points | -11.69% (-€945.64) | €0.00 | -€1,544.10 | 10/32 | 0 / 0 |
| Ample-stock control | **-0.08 points** | -8.35% (-€783.21) | €0.00 | -€1,282.92 | 10/32 | **1 / 1** |

All requested quantities matched and both ledgers passed. The ample-stock policy delivered two fewer PRD-004 units on time and in total to CUS-016. That customer requested 146 units across products; PRD-004 had 265 requested units across customers. Complete-line service also fell 0.34 points. The only changed decision involving PRD-004 reduced it from 54 to 48 units on 31 July; a bounded causal diagnosis is still required. The seven planning views accepted that decision, but the independently generated future exposed the small loss. This is exactly why the repeated-decision test is required.

Search itself averaged 0.93–1.89 seconds per decision; the slowest decision was 3.65 seconds. Each case retained 1,099–2,121 physical replays. This is bounded development runtime, not a general performance certification.

## Decision

The approach is materially more credible than the failed allocation model and produced lower simulated investment in all four cases. It is **not ready for the 18-case batch** because the ample-stock control violates the requested no-regression standard. These percentages are overlapping synthetic scenario outcomes, not additive or realised savings, and they do not pass the release gate.

Stop here. The next step is a bounded diagnosis of why the 31 July PRD-004 reduction passed all seven planning views yet lost two units in repeated operation. Do not tune parameters, open fresh seeds or start a broad batch from these four results.

Evidence: `artifacts/distributor-demo/discrete-physical-trial-01/` contains the pre-outcome contract, exact source hashes/archive, compact case reports, every customer/product regression and the summary.
