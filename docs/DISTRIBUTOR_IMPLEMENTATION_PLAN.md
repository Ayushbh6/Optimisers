# Distributor ordering demo — approved implementation contract

Approved 15 September 2026. This is separate from the locked retail investigation.

Promise: **Know what to order now, what can wait, and which customer deliveries remain at risk.**

## Delivery order

1. Implement typed operational state, chronological physical accounting, causal forecasts and a competent stock-cover comparison.
2. Implement 28-calendar-day integer-case purchasing with supplier ordering opportunities, projected service targets of baseline minus two percentage points, baseline, and baseline plus two points. Minimise average stock plus outstanding commitments, then expiry and delivery charges. Independently replay and validate proposals. Commit today only.
3. Run all 18 development cases. Select a shared forecast using rolling historical checks (four-week mean, eight-week mean, weekday-adjusted eight-week mean); select baseline safety cover from zero, three and seven working days. Freeze source, configuration and measurement hashes before opening 30 reserved cases.
4. Evaluate eight weeks plus a separately reported 30-day settlement period. Repeat with two-workday additional supplier delays and 30-day incoming freshness. Preserve all failures and regressions.
5. Only after the value gate, finish FastAPI + React/TypeScript/Vite UI, guided ordinary-trading example, all six families, buyer edits and locks, projected trade-offs, source inspection, checked draft order exports, evidence page, and local CSV import/correction. Public mode accepts only example data.
6. Package one-command local launch and portable container; no purchased hosting or publication in this task.

## Immutable rules

Keep retained v2 data, generation settings, original pipeline and locked plan unchanged. Planner inputs exclude evaluator records, seeds and latent generation parameters. Each policy evolves independently; both use identical physical dispatch and accounting. Recorded customer requests, not shipments, feed forecasts. Daily product demand is booked units plus the positive forecast remainder; no double counting. Promotions have no invented uplift. Unknown receipt freshness defaults to an explicitly labelled 60-day assumption.

Physical sequence: expiry → released notices and receipts → new requests → purchasing → dispatch → cancellations → closing. Respect dated terms, cases, product and supplier minimums, fees, weekly allowance, capacity before dispatch, customer freshness, whole-line and lateness rules. Undelivered orders and customer obligations never disappear. Quantities are individual units; money is integer euro cents.

## Quantitative gate (not a correctness test)

At least two non-ample families, with at least four of five reserved seeds each, must achieve either at least +2 percentage points on-time units with stock plus commitments no more than +5%, or at least 10% less stock plus commitments with service no worse than -1 point. Complete-line service in a winning family must not fall by more than one point. Any individual service regression over five points blocks an overall headline. Claimed wins cannot increase expiry or ending stock plus commitments over the baseline by more than 5%, with a €25 near-zero tolerance. Ample stock must show restraint; ties are acceptable. Claimed directions must survive both sensitivity scenarios.

Freeze before reserved evaluation. Do not tune on reserved results or change scenarios to manufacture a win. If the gate fails, report results and stop before polishing an improvement claim.

## Product completion

Buyer workflow: inspect data → resolve explicit input errors → inspect risks → compare proposals → edit/lock quantities and assumptions → recalculate → export valid draft supplier orders. Record original imports and explicit corrections; never impute missing costs. Real imports are local-only and never acquire synthetic savings claims. Public sessions expire after 24 hours; jobs are bounded and cancellable; exports reject stale/invalid plans and escape spreadsheet formulas. First checked recommendation target five seconds, alternatives at most 30 seconds, with honest fallback status.

Tests cover independent ledger reconciliation, hand examples, information isolation, deterministic supply, all constraints, no-order/infeasible cases, imports, sessions, stale plans, browser workflow, accessibility and five simultaneous demo sessions. Keep compact final artifacts under artifacts/distributor-demo; remove only task-created intermediate copies after verification.

Synthetic capability is not proof of client savings, forecast accuracy in real firms or willingness to pay. External outreach requires separate authorisation.
