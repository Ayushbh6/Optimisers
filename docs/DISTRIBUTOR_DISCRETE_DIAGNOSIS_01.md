# Discrete purchasing diagnosis 01 — ample-stock service loss

Completed 17 September 2026. Synthetic development evidence, not client outcomes. This diagnosis changed no planner logic and opened no wider case or fresh seed.

## Finding

The physical engine is correct. Candidate generation and the seven fixed-plan replays are also internally correct. The failure comes from **freezing future stock-cover quantities instead of allowing future buyer decisions to react to today's edited basket**.

Current flow:

Today's edited basket → replay the same fixed future purchase quantities → report a safe six-unit reduction.

What repeated operation actually does:

Today's edited basket → later stock-cover decisions see different stock → later supplier baskets and weekly-budget choices change → receipts move to different dates → a customer delivery can change.

That missing feedback is the modelling defect.

## Exact customer loss

One order line regressed: `F-CO-000201-L01`, 16 Mint Drops (`PRD-004`) for `CUS-016`, created 19 August and due 21 August.

- Stock cover shipped all 16 on time.
- The discrete policy shipped 14 and cancelled two.
- The customer accepts partial delivery, requires 60 days freshness and allows no lateness.
- Every available unit was freshness-eligible. No expiry, warehouse-capacity rejection or supplier disruption caused the loss.

The 31 July edit reduced Mint Drops from 54 to 48 units. In repeated operation, stock cover later compensated by increasing the 14 August order from 24 to 30 units. Both paths purchased 138 Mint Drops across 31 July–21 August; the optimiser did not remove six units overall—it moved them two weeks later. The compensating stock arrived 22 August, one day after the affected order was due.

## Causal replay

Five paths were fixed before detailed inspection:

| Path | Service | Average stock + commitments | Result |
|---|---:|---:|---|
| Stock cover throughout | 96.63% | €9,376.13 | Reference |
| Optimiser throughout | 96.55% | €8,592.91 | Two-unit loss |
| Optimiser before 31 July, then stock cover | 96.63% | €8,723.77 | No loss |
| Optimiser through 31 July, then stock cover | 96.55% | €8,717.99 | Same two-unit loss |
| Optimiser except 31 July | 96.63% | €8,598.69 | No loss |

Therefore:

- Earlier optimiser edits do not cause the regression.
- The 31 July edit alone causes it even when every later decision returns to stock cover.
- Removing only that edit restores both units while retaining every other optimiser decision.
- Later optimiser edits neither create nor repair this loss.

The isolated edit lowers eight-week average investment by only €5.78, raises ending stock plus commitments by €10.44, and loses two deliveries. It is operationally dominated in the realised repeated path.

## Why seven views accepted it

At 31 July, Mint Drops had zero stock, 24 incoming units and 41 already-booked units. The evaluator's remaining request list within the 28-day horizon totalled 96 units, but 15 of those units were created and released on 31 July and were already represented in the booked state; genuinely later-created demand totalled 81 units. The planning remainders were 64 nominal, 13 lower, 114 higher and 35/87/99/100 across the four historical patterns.

The higher view therefore contained more projected units than the genuinely later-created demand. The issue was not simply too little total demand. Its demand was spread into daily six- or seven-unit cohorts; only six units were assigned to `CUS-016` on 21 August, versus the realised 16-unit order. Other units occurred after the next receipt. Every fixed-plan view consequently finished with exactly six fewer Mint Drops and no delivery change.

The fixed schedules also prevented future purchasing feedback. When the same higher view was rerun with stock cover recalculated at every future ordering date:

1. Reducing Mint Drops by six on 31 July made stock cover add six Mint Drops on 7 August.
2. The weekly allowance had €823.60 left. The extra Mint Drops used €31.32; adding the 24-unit Corn Bites (`PRD-008`) minimum would then exceed the allowance by €26.30.
3. Corn Bites moved from the 7 August supplier basket to 14 August.
4. Its receipt moved from 15 to 22 August.
5. A four-unit higher-view order due 21 August shipped on 22 August, reducing on-time service by 0.20 points.

Under adaptive replay, the existing higher-demand view rejects the 31 July candidate. This establishes that a new demand parameter or tuned buffer is not required to explain or catch this case.

## What is and is not broken

Working correctly:

- exact warehouse dispatch, freshness, expiry, capacity and accounting;
- case, product minimum, supplier minimum and dated-term checks;
- deterministic candidate generation;
- physical results for each purchase schedule actually supplied to replay.

Incomplete:

- candidate replay treats future stock-cover quantities as fixed data;
- it therefore misses later budget and supplier-basket changes caused by today's edit;
- reported cash and leftover consequences can describe the fixed schedule rather than the repeated buyer policy.

## Recommended correction

For each candidate and each required demand view:

1. Commit only today's candidate basket.
2. Advance the same physical warehouse.
3. On each later supplier date, recalculate the competent stock-cover basket from that candidate's evolved state.
4. Enforce the same weekly budget, supplier grouping, capacity, terms and delivery rules.
5. Reject the candidate against an independently evolving stock-cover reference for that same view.

Add a hand regression reproducing the six-unit reorder and cross-product budget displacement. Then run a new four-case trial under a new source contract. Only a clean four-case result should unlock the 18 development cases. Fresh seeds 91301–91305 and website work remain closed.

Evidence: `artifacts/distributor-demo/discrete-physical-diagnosis-01/` retains the predeclared contract, source archive, exact five-path trace, fixed-view audit, adaptive-view audit, supplier-basket/budget trace and reproducible scripts. Generated databases were removed.
