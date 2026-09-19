# Bounded purchasing review: understand the business before adding complexity

Synthetic demonstration records, not client outcomes. Completed after the three failed development batches. This review does not reopen reserved seeds or claim that the release gate passed.

## What the records show

The retained default is the supplier-disruption example, not an ordinary-trading sample. Its 26 historical weeks contain 7,594 requested units, 7,068 dispatched, 453 cancelled and 73 still open at the history boundary. These totals reconcile; unfinished orders mean this is not a final service score for every historical request.

Closing stock is €5,858.52, with another €1,516.50 committed to undelivered goods. Historical expiry write-offs total €3,633.50. Honey Drops alone accounts for €2,571.93 (70.8%). Most expiry cost (€3,255.39) comes from received stock, rather than opening lots (€378.11).

Honey Drops has a 96-unit product minimum, costs €6.97 per unit and was ordered in nine 96-unit purchases during history. Historical requests total only 196 units; the most recent eight weeks contain 73 units, about 9.1 per week. Its closing stock is 265 units. The minimum is therefore about 10.5 weeks of recent demand. Recorded receipts have 76 days of remaining life, and most requested Honey Drops units belong to customers requiring 30 days remaining on delivery. This combination explains why order size and freshness deserve review. Demand averages are not guarantees or proof that a particular past purchase was avoidable.

Shortages coexist with that excess: three other products account for 244 of the 453 cancelled units. At cancellation-day close, 308 cancelled units coincide with no stock left for the product; 14 coincide with stock left but none meeting that customer's freshness requirement. Another 131 coincide with some eligible stock. Those are observations after other deliveries, not a causal claim that every cancellation could have been prevented; whole-line rules and earlier customer priority need consideration.

## Bounded decision test

Decision: can the buyer change today's supplier basket without losing deliveries or breaking commercial rules?

Use the first three Wednesdays of June (4, 11, 18), selected before inspecting screen outcomes. Read each snapshot after that day's notices, receipts and requests, but before purchasing and dispatch. Keep the eight-week forecast, 60-day unknown freshness assumption, cases, supplier minimums, prices, weekly budget, capacity, expiry and customer rules unchanged. Retain all other dated baseline purchases in the 28-day horizon.

Review each baseline purchase line, at most eight per date, in stable product order. The three development variants are:

1. Move the entire line to the next supplier order day.
2. Make that move, topping up an already ordered line at the least extra purchase cost if today's supplier minimum would otherwise fail.
3. Omit the current line and perform the same minimum repair, without forcing that line into next week's budget. All other baseline future purchases stay fixed.

This sequence was developed from observed conflicts: deferral broke supplier minimums; repaired deferral could exceed next week's budget. It was not a frozen out-of-sample examination. There are **15 distinct edits** in the final reproducible screen. Every edit is evaluated through the physical dispatch engine, not the original solver's allocation approximation. Reject any line-level loss in on-time or total deliveries, increased expiry or increased terminal stock/commitments in nominal, lower and higher demand views. The two surviving substitutions receive four additional historical request-pattern checks each.

An initial pre-receipt diagnostic used the wrong decision boundary for this workflow. It produced no accepted edits and is superseded. The loader now exposes the already existing `before_ordering` snapshot phase; an explicit test verifies inclusion of released requests and exclusion of today's purchasing/dispatch. The original end-of-day loader default and previous frozen batch archives remain unchanged.

## Results

| Decision date | Supplier basket change | Conditional result |
|---|---|---|
| 4 June | Replace 96 Honey Drops plus 18 Lentil Soup units with 48 Lentil Soup units | Goods spending falls from €770.64 to €270.72; supplier charge unchanged. The €250 minimum is still met. Average stock plus commitments falls €499.92 in the nominal 28-day projection, with no delivery loss. |
| 11 June | A different baseline basket substitution | €6.96 less average stock plus commitments: a small result, not a showcase headline. |
| 18 June | Reviewed purchase-line edits | No acceptable improvement. |

The two substitutions have no line-level delivery losses in the four additional historical patterns. Their full investment, expiry and terminal balances remain in the evidence. All other edits and conflicts remain visible. A rejection is useful information; it prevents an apparently cheaper basket from silently breaking customer commitments.

**This is a credible lead for a feature, not proof of realised savings or a completed optimiser.** The main example's nominal capital improvement is about 6.7%, below the overall ten-percent route; this three-date screen is not the eight-week paired evaluation or reserved release test. Historical-pattern checks and error ranges are conditional challenges, not statistical guarantees. The examples were examined during development and must not be sold as unseen results.

## What changed and what remains

The bounded purchasing-review module can now test complete supplier-basket edits using the actual dispatch rules, identify exact conflicts and disclose every harmed line. Small hand-calculated checks verify delayed commitment costs, whole-line cancellation and supplier-minimum rounding. Snapshot tests protect the decision boundary and later-data isolation. The active repository suite passes **162 tests**.

The production MILP remains unchanged; this feature is not wired into automatic recommendations, and no large batch or fresh evaluation was started. The next justified experiment would test this specific basket-composition rule on a small predeclared set of additional development decisions, including shortages and a no-change control. Only if that survives should it become a candidate for repeated purchasing evaluation. Do not launch that experiment automatically.

## Reproduce and inspect

Run from the repository root into a new output directory:

```sh
PYTHONPATH=. .venv/bin/python artifacts/distributor-demo/bounded-review-01/reproduce.py --output artifacts/distributor-demo/bounded-review-repeat
```

Evidence: `artifacts/distributor-demo/bounded-review-01/verified/` retains the fixed dates, input/source identities, all 15 edits, eight historical-pattern checks and compact summary. `history-profile.json` and `cancellation-observations.json` retain the business observations. `history_queries.sql` documents source queries. `tests.txt` records full verification. No evaluator database is read by this screen.
