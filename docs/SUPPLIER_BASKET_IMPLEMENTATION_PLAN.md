# Supplier Basket Review — Authoritative Implementation Plan

**Status:** All seven implementation phases completed to technical release-candidate standard on 18 September 2026. The hand truth, messy exports, reconciliation, exact physical decision, explanations, supplier drafts, browser application and container launch are frozen and reproducible. External buyer usability and pilot willingness remain commercial validation, not completed evidence.

Read this with:

- `docs/SUPPLIER_BASKET_SHOWCASE_BRIEF.md`
- `docs/TARGET_CLIENTS.md`
- `docs/REPO_RULES.md`

## Product contract that every phase must preserve

### Main selling point

> **Turn messy distributor exports into a supplier-ready weekly purchase plan that shows where cash can be released without putting booked customer deliveries at risk.**

### Marquee hypothesis

> Using only information available at ordering time, the product can reconcile messy operational records and identify lower-cash supplier-basket alternatives that preserve booked-order fulfilment exactly. When no safe alternative exists, it retains the buyer's original plan.

### Claim boundary

The showcase is a clearly labelled synthetic case study. It may prove that the software correctly handles the frozen example records. It may not claim realised client savings, general forecast accuracy, universal optimisation performance or willingness to pay.

## Universal phase rules

1. **One phase at a time.** Work on the next phase begins only after the current gate is explicitly passed.
2. **Expected answers come first.** Hand-calculated or independently specified truth is frozen before implementation output is inspected.
3. **Tests prove correctness, not success.** An automated test may assert a frozen hand-calculated answer; it may not invent a target such as “savings must exceed 10%.”
4. **No silent data repair.** Every source row remains traceable. Material ambiguity requires buyer confirmation or blocks the recommendation.
5. **No future information.** A purchasing decision uses only facts available at its declared decision timestamp.
6. **Negative outcomes remain visible.** Unsafe alternatives and no-change results are required product behaviour, not failures to hide.
7. **No phase-end evidence is overwritten.** A material contract change creates a new version and retains the earlier result.
8. **Lean evidence only.** Retain contracts, fixtures, hashes, compact reports and final screenshots; remove reproducible scratch after verification.

## Authoritative testing hierarchy

Each phase uses the strongest applicable evidence in this order:

1. **Frozen business truth:** facts and expected answers written without using the implementation.
2. **Independent calculation or reconciliation:** a second route reproduces the answer.
3. **Automated behavioural tests:** the implementation matches the frozen truth and rejects invalid inputs.
4. **End-to-end evidence:** the same result survives the complete user workflow.
5. **Human buyer review:** a distributor-aware reviewer can understand the decision, assumptions and next action.

Implementation-generated output can never be its own expected answer.

## Phase map

| Phase | Outcome | Authoritative gate |
|---|---|---|
| 1. Business case contract | Three hand-calculated purchasing cases | Business facts and answers independently reproduce exactly before code or data generation |
| 2. Messy raw-data package | Plausible exports plus golden clean truth | Every raw row is accounted for; every issue is correctly classified |
| 3. Import and reconciliation | Raw exports become a traceable operational ledger | Output exactly matches the Phase 2 golden truth with zero unexplained differences |
| 4. Purchasing decision core | Original basket and bounded alternatives are physically checked | Positive, unsafe and no-change outcomes exactly match Phase 1 |
| 5. Explanation and export | Buyer-readable recommendation and supplier draft | Every displayed/exported number traces to the selected decision |
| 6. Client-facing application | Complete upload-to-export workflow | A new user completes all three cases without developer intervention |
| 7. Showcase release | Reproducible, honest, sellable demonstration | Clean end-to-end run proves the complete USP without unsupported claims |

## Phase 1 — Freeze the business case contract

### Goal

Prove on paper that the showcase contains a real, understandable purchasing opportunity before creating data or software.

### Scope boundaries

- One fictional food/FMCG distributor.
- One warehouse and euro-denominated purchasing.
- Two suppliers and approximately six to eight products—only enough to make supplier-basket behaviour realistic.
- Approximately four to six customers with booked order lines.
- A 28-day physical consequence window.
- Quantities use one declared base unit per product; cases convert exactly to that unit.
- Booked customer deliveries are the hard protection promise.
- Unknown future customer demand is not used to manufacture or validate the positive result.
- No selling margins, lost-sale penalties, shortage prices or invented profit calculation.
- Three independently understandable decision cases: positive, unsafe and no-change.

These are showcase design limits, not claims about Lona, Matt Import or distributors generally.

### Work package 1.1 — Common operational rules

Declare once for all three cases:

- decision timestamp and event order within each day;
- supplier order weekdays and working-day lead times;
- case sizes, product minimums and supplier basket minimums;
- dated unit costs and delivery charges;
- available purchasing allowance;
- opening stock by lot, receipt date and expiry date;
- known incoming quantities and expected arrivals;
- booked customer lines, due dates, partial-delivery rule, lateness allowance and freshness rule;
- receipt, dispatch, expiry and capacity sequence;
- 28-day cash, stock, incoming-commitment and delivery measurements.

Every fact must be either a visible illustrative assumption or derived from another declared fact.

### Work package 1.2 — Positive case

Create a valid but inefficient buyer basket in which a supplier minimum, product minimum or case pack causes avoidable cash and stock.

The alternative must be legitimate because it changes basket composition—not because the buyer forgot a booked order or used an obviously invalid baseline.

Required hand result:

- the buyer's basket satisfies every purchasing rule;
- the proposed basket also satisfies every rule;
- proposed immediate cash is lower by an exact euro amount;
- every booked unit ships on the same promised date as under the buyer basket;
- expiry does not increase;
- ending stock plus incoming commitments does not increase;
- changed products, arrival dates and leftover stock are explicitly shown.

### Work package 1.3 — Unsafe cheaper case

Create an alternative that looks attractive on purchase cash but is operationally unsafe.

The unsafe reason must be concrete, such as:

- a booked line misses its due date;
- supplier or product minimum is broken;
- weekly purchasing allowance is exceeded;
- receipt capacity is exceeded;
- required freshness cannot be met;
- dated terms make the proposed order invalid.

Required hand result:

- exact apparent cash reduction;
- exact failed rule or customer line;
- exact date and quantity of the consequence;
- expected product response: reject the alternative and explain why.

### Work package 1.4 — No-change control

Create a basket that is already appropriate: every line is needed, valid and timed correctly.

Required hand result:

- all declared bounded removals/reductions either break a rule or harm a booked delivery;
- increases do not reduce cash or stock commitments;
- expected product response: retain the buyer's basket without inventing an opportunity.

### Work package 1.5 — Messiness specification

Specify the raw-data issues that Phase 2 will encode. Each issue must have a business cause and expected treatment.

Minimum coverage:

| Issue | Expected treatment |
|---|---|
| A product or supplier alias with one unambiguous match | Safe automatic normalisation with visible provenance |
| Case versus individual-unit ambiguity | Buyer confirmation before quantities are accepted |
| Duplicate followed by a clear cancellation or amendment | Deterministic resolution with both source rows retained |
| Partial receipt with a revised expected date | Outstanding quantity and revised arrival remain visible |
| Missing or contradictory decision-critical term or stock fact | Hard blocker until resolved |

No decorative spelling errors or random missing cells are added merely to make the files look messy.

### Work package 1.6 — Hand-calculation pack

For every case, independently calculate:

1. opening usable stock by product and lot;
2. known incoming stock and arrival date;
3. booked customer requirements by due date;
4. buyer basket cases, units, line values and supplier charges;
5. proposed basket cases, units, line values and supplier charges;
6. daily receipts, dispatches, expiry and closing stock for 28 days;
7. booked on-time units and complete lines;
8. immediate purchasing cash;
9. average and ending stock plus incoming commitments at purchase cost;
10. the final accept/reject/retain verdict and plain-language reason.

Stock must reconcile on every day:

`opening stock + receipts - shipments - expiry - explicit adjustments = closing stock`

No unexplained adjustment is permitted.

### Work package 1.7 — Independent review

A second calculation must reproduce the case results without importing values from the first calculation. The review checks:

- arithmetic and unit conversions;
- supplier-basket validity;
- receipt and dispatch timing;
- freshness and expiry eligibility;
- cash and fee totals;
- stock/commitment totals;
- booked fulfilment comparison;
- decision-time information boundary;
- whether the opportunity is understandable and commercially plausible.

### Phase 1 retained deliverables

When Phase 1 is executed, retain only:

- `docs/showcase/phase-1/BUSINESS_CASE_CONTRACT.md`
- `docs/showcase/phase-1/OPERATIONAL_RULES.md`
- `docs/showcase/phase-1/DATA_ISSUE_CONTRACT.md`
- `docs/showcase/phase-1/HAND_CALCULATION_REVIEW.md`
- `artifacts/supplier-basket-showcase/phase-1/expected-results.json`
- `artifacts/supplier-basket-showcase/phase-1/contract.json`

The machine-readable files will contain exact facts, expected answers, document hashes and version identity. They will not be generated from future application code.

### Phase 1 authoritative tests

Phase 1 passes only when all checks below are true:

- [x] All quantities are positive integers in declared base units.
- [x] Every basket uses whole cases and respects product minimums.
- [x] Supplier minimums, order days, dated terms, charges and budget reconcile exactly.
- [x] Every lot and incoming line has a traceable source and date.
- [x] Every booked line has an exact physical fulfilment outcome.
- [x] Positive case: lower exact cash, unchanged booked delivery dates, no higher expiry or ending commitments.
- [x] Unsafe case: lower apparent cash but one exact, explainable rejection reason.
- [x] No-change case: no bounded lower-cash survivor protects all booked deliveries.
- [x] The 28-day daily stock ledger balances without unexplained adjustments.
- [x] A second calculation reproduces all cash, stock and delivery results.
- [x] Only decision-time information is used.
- [x] A non-technical buyer can understand each verdict in five minutes.
- [x] The case remains clearly synthetic and makes no historical savings claim.

### Phase 1 stop conditions

Stop and redesign Phase 1—not the software—if any of these occur:

- the positive result depends on an incompetent or invalid buyer basket;
- the opportunity exists only because future customer orders are revealed;
- the euro result cannot be reproduced from visible quantities, costs and fees;
- the unsafe alternative requires a contrived rule that a serious buyer would dismiss;
- the no-change case contains an overlooked valid improvement;
- the data messiness cannot be resolved without silently inventing a decision-critical fact;
- the story requires more than a short buyer conversation to explain;
- the same product facts produce contradictory answers across the contract documents.

### Phase 1 go decision

Phase 2 begins only after a written review records:

- `PASS` for every authoritative test;
- exact contract and expected-result hashes;
- the approved positive, unsafe and no-change verdicts;
- confirmation that the USP and marquee hypothesis still describe what the cases demonstrate;
- explicit approval to generate the messy raw files.

## Phase 2 — Build the messy raw-data package

**Execution status:** Technical gate passed 18 September 2026. See `docs/showcase/phase-2/PHASE_2_REVIEW.md`.

### Deliverables

- Small CSV/XLSX-style exports for products, suppliers/terms, stock, customer orders, purchase orders and receipts/amendments.
- Original-row identifiers and source-system labels.
- A golden normalized ledger derived from the frozen Phase 1 truth.
- A complete issue register linking each deliberate defect to its business cause and expected treatment.

### Authoritative tests and guard

- Every source row is accounted for exactly once as accepted, superseded, confirmed or blocked.
- Golden totals match Phase 1 quantities, cash and dates exactly.
- Removing the deliberate messiness yields the same operational truth.
- No invalid row is allowed to influence a recommendation silently.
- A distributor-aware review judges the exports plausible.

**Go only if:** the files look operationally recognisable and independently reconcile to Phase 1 with zero unexplained difference.

**Stop if:** messiness is decorative, truth is ambiguous, or the records make the positive case obvious through artificial labels.

## Phase 3 — Build import and reconciliation

**Execution status:** Technical gate passed 18 September 2026. See `docs/showcase/phase-3/PHASE_3_REVIEW.md`.

### Deliverables

- File parsing, column mapping and unit normalization.
- Original-row preservation and provenance.
- Issue register with automatic, confirmation-required and blocking statuses.
- Reconciled current stock, incoming and booked-commitment ledger.

### Authoritative tests and guard

- Golden-file tests reproduce the Phase 2 normalized ledger exactly.
- Re-import is deterministic and idempotent.
- Aliases, units, amendments, partial receipts and hard blockers behave exactly as contracted.
- Quantity, cash and record-count reconciliation is visible.
- Changed input invalidates stale downstream decisions.

**Go only if:** all three raw cases produce the correct ledger and unresolved critical ambiguity prevents planning.

**Stop if:** any correction loses provenance, silently changes a business fact or requires case-specific hardcoding.

## Phase 4 — Build the purchasing decision core

**Execution status:** Technical gate passed 18 September 2026. See `docs/showcase/phase-4/PHASE_4_REVIEW.md`.

### Deliverables

- Exact reproduction of the buyer's original basket.
- Bounded integer-case alternatives around that basket.
- Supplier, product, budget, capacity, dated-term and delivery-rule enforcement.
- Exact physical replay of booked deliveries.
- Deterministic lexicographic selection and no-change fallback.

### Authoritative tests and guard

- Small unit tests cover every operational rule independently.
- The full engine exactly matches all Phase 1 hand results.
- Positive case selects the frozen lower-cash basket.
- Unsafe case is rejected for the frozen reason.
- No-change case retains the original basket.
- Selected prediction exactly equals an independent replay.
- No future information, hidden score, margin or arbitrary shortage penalty is used.

**Go only if:** all three case verdicts and every reported number match the frozen contract exactly.

**Stop if:** parameters are changed to force the positive answer, or implementation output becomes the new expected truth.

## Phase 5 — Build explanation and supplier export

**Execution status:** Technical gate passed 18 September 2026. See `docs/showcase/phase-5/PHASE_5_REVIEW.md`.

### Deliverables

- Side-by-side original and proposed baskets.
- Product-level change reasons.
- Cash, arrival, delivery-risk and leftover-stock explanations.
- Supplier-ready human-readable and CSV draft purchase order.
- Explicit assumptions, confirmations and blockers.

### Authoritative tests and guard

- Every number is derived from the selected decision object.
- Export totals equal displayed totals and engine totals.
- Unsafe and no-change explanations name the correct reason.
- CSV output handles formula injection, encoding, dates and units safely.
- No synthetic evidence is presented as achieved client savings.

**Go only if:** a buyer can trace every proposed line from raw record to exported draft.

**Stop if:** the explanation is generic, contradictory or hides an unresolved risk.

## Phase 6 — Build the client-facing application

**Execution status:** Technical gate passed 18 September 2026. Automated browser operability passed; fresh-human usability remains external validation. See `docs/showcase/phase-6/PHASE_6_REVIEW.md`.

### Deliverables

- Upload and column-mapping flow.
- Issue review and buyer-confirmation flow.
- Reconciliation summary.
- Basket comparison, evidence panel and purchase export.
- Clear synthetic-example labelling and reset.

### Authoritative tests and guard

- Typed API and application contract tests.
- Browser tests for positive, unsafe, no-change and blocking flows.
- Session isolation, upload limits and stale-plan checks.
- Keyboard, contrast, reduced-motion, responsive and error-state checks.
- A fresh user completes the journey without developer intervention.

**Go only if:** the complete workflow is understandable, reliable and visibly tied to the USP.

**Stop if:** the UI hides reconciliation, jumps straight to an answer, or requires technical explanation to operate.

## Phase 7 — Freeze and validate the showcase release

**Execution status:** Technical release candidate passed 18 September 2026. External buyer recognition and willingness to pilot are intentionally unclaimed. See `docs/showcase/phase-7/SHOWCASE_RELEASE.md`.

### Deliverables

- Versioned source, raw example files and acceptance contract.
- Clean local/container launch and deterministic reset.
- Compact evidence report covering every case and regression.
- Five-minute sales walkthrough and buyer-review questions.
- Honest public claim wording.

### Authoritative tests and guard

- Clean-environment run from raw upload through supplier export.
- All lower-level and end-to-end tests pass from the frozen version.
- Declared performance targets are measured on a named environment.
- Data/session isolation and deletion behaviour are verified.
- A claim audit confirms every public statement is supported.
- A distributor-aware reviewer recognises the decision and identifies a plausible pilot conversation.

**Release only if:** the complete demonstration proves the USP under the labelled case-study conditions and all three cases remain inspectable.

**Stop release if:** the positive result is the only polished path, the control cases are hidden, or any wording implies realised client savings or general performance.

## Current next action

Run the five-minute walkthrough with a distributor buyer and record whether the workflow, constraints and proposed pilot are credible. Do not create optimiser v2 or open fresh evaluation seeds to manufacture another result.
