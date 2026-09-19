# Supplier Basket Showcase — Phase 1 Hand-Calculation Review

**Contract version:** `supplier-basket-showcase-phase-1-v1`
**Review date:** 18 September 2026
**Review verdict:** **PASS — technical Phase 1 gate**
**Next-phase status:** Blocked until the user explicitly accepts this evidence and authorises Phase 2 data generation.

## What was reviewed

The review used only the frozen facts in `contract.json`. It did not use application code, the previous distributor optimiser, evaluation seeds or a generated dataset.

Two routes were compared:

1. The first hand route used the basket, cash and dated stock tables in the business contract.
2. A separate event-by-event calculation rebuilt lots, receipts, FEFO dispatch, late units and daily exposure directly from the machine-readable facts. It then compared its results with `expected-results.json`.

The second route reproduced five primary basket replays, nine positive-case alternatives and twelve no-change alternatives. All 28 daily balances reconciled with zero stock adjustments.

## Cash arithmetic

| Case and basket | Merchandise arithmetic | Fee | Immediate cash |
|---|---|---:|---:|
| Positive buyer | `5×12×€4 + 2×12×€5 + 1×24×€10` | €20.00 | €620.00 |
| Positive proposed | `8×12×€4 + 2×12×€5` | €20.00 | €524.00 |
| Unsafe buyer | `2×12×€5 + 1×6×€8 + 1×12×€2.50` | €15.00 | €213.00 |
| Unsafe challenged | `1×12×€5 + 1×6×€8 + 2×12×€2.50` | €15.00 | €183.00 |
| Control buyer | `1×6×€8 + 2×12×€2.50 + 2×12×€1.80` | €15.00 | €166.20 |

All merchandise totals satisfy the relevant supplier minimum except the three control reductions explicitly rejected before replay. Every replayed basket is within the €800 allowance and the 250-unit receipt limit.

## Positive case review

### Exact physical result

| Measure | Buyer | Proposed | Difference |
|---|---:|---:|---:|
| Immediate cash | €620.00 | €524.00 | **−€96.00** |
| Booked units on time | 96/96 | 96/96 | 0 |
| Complete lines | 5/5 | 5/5 | 0 |
| Expired units | 0 | 0 | 0 |
| 28-day average exposure | €435.77 | €339.77 | **−€96.00** |
| Ending stock plus commitments | €355.20 | €259.20 | **−€96.00** |

Daily exposure, including the unchanged Breakfast Tea partial receipt:

| Dates | Days | Buyer per day | Proposed per day |
|---|---:|---:|---:|
| 18–20 Sep | 3 | €763.20 | €667.20 |
| 21–22 Sep | 2 | €715.20 | €619.20 |
| 23–24 Sep | 2 | €511.20 | €415.20 |
| 25 Sep–15 Oct | 21 | €355.20 | €259.20 |
| **28-day sum** | **28** | **€12,201.60** | **€9,513.60** |

The €96 difference is visible every day. Before arrival it is lower incoming commitment; after arrival it is lower stock value. The 28 September Tea receipt merely moves €57.60 from incoming to stock and changes neither total.

### Candidate check

The declared bounds regenerate nine unique alternatives. Two are safe minimum repairs, but the Tomato Soup repair has the lowest exposure and cash. Four alternatives lose booked service, two safe increases hold more stock, and one increase exceeds the weekly allowance. No output was tuned to make the selected basket win.

## Unsafe case review

| Measure | Buyer | Challenged | Difference |
|---|---:|---:|---:|
| Immediate cash | €213.00 | €183.00 | **−€30.00** |
| Booked units on time | 54/54 | 42/54 | **−12** |
| Complete lines | 4/4 | 3/4 | **−1** |
| Failed line | None | `UNS-CO-002` on 24 Sep | 12 Nougat Bars late |
| Expired units | 0 | 0 | 0 |
| 28-day average exposure | €52.71 | €117.00 | +€64.29 displayed |
| Ending stock plus commitments | €0.00 | €90.00 | +€90.00 |

The opening 12 Nougat Bars ship on 21 September. On 24 September the challenged receipt contains only 12 Nougat Bars against a 24-unit line. Partial dispatch therefore leaves exactly 12 units late. The remaining €90 is €30 of extra Pasta plus €60 of undelivered Nougat commitment.

**Verdict reproduced:** reject the cheaper basket and retain the buyer basket.

## No-change control review

The buyer basket ships all 54 units across four lines, expires nothing and ends at zero stock and zero undelivered commitment.

| Candidate group | Count | Result |
|---|---:|---|
| Direct one-case reductions | 3 | Rejected before replay: merchandise falls below €150 |
| One-case increases | 3 | Delivery-safe but cash and ending stock increase |
| Smallest two-line minimum repairs | 6 | Supplier-valid but each loses 6 or 12 booked units |
| Safe lower-exposure survivors | **0** | None |

The twelve exact candidate results are frozen in `expected-results.json`. The buyer basket is not retained because of a hidden score; it is retained because every cheaper reduction is invalid or physically unsafe and every safe increase is worse.

## Daily stock identity

The independent route checked every product on every day:

`opening usable units + receipts - dispatches - expiry = closing usable units`

| Check | Result |
|---|---:|
| Primary basket replays | 5 |
| Daily periods per replay | 28 |
| Positive bounded alternatives regenerated | 9 |
| Control bounded alternatives regenerated | 12 |
| Unexplained stock adjustments | **0** |
| Expired units | **0** |
| Future orders or evaluator facts used | **0** |

## Phase 1 authoritative checklist

| Test | Result | Evidence |
|---|---|---|
| Transaction quantities are positive integers in base units | PASS | Machine-readable contract |
| Ordered quantities are whole cases and meet product minimums | PASS | Basket arithmetic and candidate audit |
| Supplier minimums, order days, terms, charges, budget and capacity reconcile | PASS | Cash table and prechecks |
| Every lot and incoming line has source and date | PASS | `contract.json` source IDs |
| Every booked line has an exact physical outcome | PASS | Exact replay and failed-line record |
| Positive result lowers exact cash without delivery, expiry or terminal regression | PASS | −€96.00; 96/96 units; zero expiry |
| Unsafe case has one exact explainable rejection | PASS | `UNS-CO-002`, 24 Sep, 12 units |
| No-change case has no safe lower-exposure survivor | PASS | All 12 bounded alternatives reviewed |
| All 28-day ledgers balance | PASS | Independent event calculation; zero adjustments |
| Second calculation reproduces results | PASS | Five primary and 21 bounded replays matched |
| Only order-time information is used | PASS | All bookings and terms predate 09:00 decision |
| Verdicts are understandable in a five-minute buyer walkthrough | PASS | Three plain cause-and-effect case summaries; no formula required |
| Synthetic claim boundary is explicit | PASS | Every retained contract labels it |

## Stop-condition review

No Phase 1 stop condition fired:

- The buyer baskets are valid and operationally defensible.
- The positive result does not use future customer demand.
- Every euro is reproduced from visible units, costs and fees.
- The unsafe failure is an ordinary booked-order shortage, not a contrived penalty.
- The control contains no overlooked bounded improvement.
- Data ambiguity is confirmed or blocked rather than silently repaired.
- The same facts produce the same answer in every retained file.

## Honest limitation

This is an internally reviewed synthetic contract. It proves arithmetic coherence and defines what later software must reproduce. It does **not** prove that a real distributor has this opportunity or that an external buyer accepts the assumptions. External distributor validation remains a later showcase-release check.

## Gate decision

**Technical Phase 1: PASS.** The USP and marquee hypothesis still match the three cases. Phase 2 remains unopened until the user reviews this checkpoint and explicitly authorises raw-data generation.
