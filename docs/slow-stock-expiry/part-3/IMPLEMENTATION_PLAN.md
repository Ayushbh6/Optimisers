# Stock Watch — Part 3 implementation plan

**Status:** Planned, 18 September 2026. Work begins one phase at a time. A failed gate stops the work at that phase; it does not trigger parameter tuning or a larger dataset.

Read first:

- `docs/slow-stock-expiry/part-1/OPPORTUNITY_DIAGNOSIS.md`
- `docs/slow-stock-expiry/part-2/PRODUCT_CONTRACT_V2.md`
- `docs/REPO_RULES.md`

## Universal rules

1. Write and independently check expected answers before writing the code that produces them.
2. Use only information available at the declared review date.
3. Keep every raw row traceable; never silently fix a decision-critical fact.
4. Treat booked customer orders and shelf-life requirements as hard protection rules.
5. Apply the same physical rules and demand views to the buyer plan and every alternative.
6. Keep unsafe and no-action outcomes visible.
7. Retain compact contracts, hashes, reports and negative outcomes. Remove only task-created scratch after verification.
8. Do not claim realised savings or demand certainty from synthetic records.

## Phase map

| Phase | What is built or proved | Gate to proceed |
|---|---|---|
| 1. Hand-calculated business truth | Three small, complete weekly inventory cases | Independent calculation exactly reproduces stock, expiry, service and cash outcomes. |
| 2. Messy record package | Plausible raw exports and a clean expected ledger | Every source row is accounted for and no issue gives away the answer. |
| 3. Import and stock position | Traceable lot, order and incoming-stock position | Raw records reproduce the expected ledger exactly; unresolved critical facts block decisions. |
| 4. Exact inventory decision | Run-out, expiry and bounded purchase actions | The engine exactly matches all Phase 1 answers in every demand view. |
| 5. Buyer explanation and drafts | Clear action list and supplier purchase amendment | Every displayed and exported number traces to the selected replay. |
| 6. Client-facing application | Complete review workflow | A fresh user completes positive, unsafe and control paths without help. |
| 7. Release evidence | Repeatable, honest showcase | Clean run, complete test suite, claim audit and five-minute walkthrough all pass. |

## Phase 1 — Freeze the hand-calculated business truth

**Goal:** prove on paper that the three buyer instructions are real, understandable and physically possible.

### Work

- Declare one review date, warehouse event sequence and 28-day horizon.
- Declare products, case sizes, lot receipts, `use by`/`best before` classification, customer shelf-life rules, supplier terms, costs and cut-offs.
- Freeze booked orders and all demand views before any implementation result is inspected.
- Hand-calculate the buyer plan and proposed action plan day by day.
- Include the three cases from the approved product contract: balanced action plan, unsafe-looking reduction, healthy control.
- Independently reproduce all results through a second calculation route.
- Specify the raw-data messiness to be added later and its required treatment.

### Required proof

- Every lot balances each day: opening + receipts − dispatches − expiry = closing.
- Every “order now” quantity is a whole-case quantity and arrives before the shortage it prevents.
- Every “buy less” action respects change cut-offs and remains safe in every demand view.
- Every booked order is either fulfilled with the stated lot and shelf life, or the action is rejected.
- Expiry and cash before/after are exact and traceable.
- The unsafe case has one exact business reason for rejection.
- The control contains no valid better action in the declared search bounds.

### Stop

Stop if the action plan relies on a foolish baseline, hidden future demand, a made-up supplier right, a shelf-life violation, or an explanation that a buyer cannot follow quickly.

### Retain

- business-case contract;
- operational-rules contract;
- data-issue contract;
- independent hand-calculation review;
- compact expected-results and contract JSON with hashes.

## Phase 2 — Create the messy record package

**Goal:** turn the frozen truth into recognisable but imperfect operational exports.

### Work

- Create small exports for products, lots, receipts, stock snapshots, customer orders, open purchases, supplier terms and recent demand.
- Add only business-caused messiness: aliases, case/unit ambiguity, amended purchase lines, partial receipts, revised dates and a missing decision-critical term.
- Write a golden clean ledger and issue register before importer work begins.

### Gate

- Every raw row is accepted, superseded, confirmed or blocked exactly once.
- Removing the deliberate messiness gives the same clean truth.
- The files contain no “recommended action” column or hidden result.
- The positive action is not obvious merely from a label or filename.

### Stop

Stop if the records require silent guessing, the messiness is decorative, or the resulting data makes the desired answer inevitable without replay.

## Phase 3 — Import and reconcile the current position

**Goal:** turn raw files into a buyer-checkable lot-level position.

### Work

- Parse files, normalize unambiguous aliases and units, preserve source provenance.
- Classify issues into automatic, confirmation-required and blocking.
- Reconcile available, reserved, quarantined, incoming and committed stock by product and lot.
- Separate `use by` from `best before`; preserve dates and storage facts.

### Gate

- The reconciled ledger exactly matches the Phase 2 golden ledger.
- Re-import is deterministic.
- A missing expiry date, customer shelf-life rule, supplier cut-off or quantity unit blocks a decision when material.
- Changed input invalidates a stale decision.

### Stop

Stop if a correction loses source provenance or case-specific code is required to reach the expected answer.

## Phase 4 — Build the exact inventory decision engine

**Goal:** replay the real lot position and select only safe actions.

### Work

- Reproduce the buyer’s current open-purchase plan.
- Generate a small deterministic set of valid actions: order now, keep, reduce, defer or cancel.
- Replay every feasible action through lot-level receipt, eligible FEFO allocation, customer shelf-life, booked dispatches, demand views and expiry.
- Apply the frozen filter order and stable tie-breaker from the product contract.
- Report run-out dates, at-risk lots, rejected actions and no-action results.

### Gate

- Unit tests cover quantities, lots, dates, FEFO eligibility, change cut-offs, supplier terms, case sizes and each demand view.
- All Phase 1 results match exactly.
- The chosen result equals an independent replay.
- No future data, hidden penalty or weighted business score appears in the decision.

### Stop

Stop if settings are tuned after results are known or the implementation becomes the source of the expected answers.

## Phase 5 — Explain the action and create drafts

**Goal:** make the answer usable by a buyer, not merely mathematically correct.

### Work

- Create a simple weekly action list: order now, buy less, delay/cancel, use first, review, no action.
- Show before/after cash, run-out dates, expiry risk, booked delivery protection and remaining stock.
- Produce a supplier amendment/order draft and a separate residual-risk list.
- Keep calculation evidence available but secondary.

### Gate

- Every displayed/exported value comes from the selected replay.
- Export totals equal screen totals.
- Unsafe and healthy cases explain why no change is made.
- The wording separates known facts from projected demand.

### Stop

Stop if the page looks like a generic stock dashboard, hides risk, or suggests realised savings.

## Phase 6 — Build the client-facing workflow

**Goal:** a non-technical buyer can follow the decision end to end.

### Work

- Choose a labelled example, review records and resolve needed confirmations.
- Read a plain-language “this week” action list.
- Inspect one simple before/after chart and optional detailed audit.
- Download the relevant supplier draft or residual-risk list.

### Gate

- Browser checks pass for the balanced, unsafe and healthy cases.
- Keyboard, contrast, mobile layout, errors, session isolation and stale-plan behaviour are tested.
- A fresh user can explain the recommended action and its risk without developer help.

### Stop

Stop if using the product needs an explanation of the underlying algorithm.

## Phase 7 — Freeze release evidence

**Goal:** provide a small, repeatable, honest sales demonstration.

### Work

- Freeze source, raw fixtures, contracts, hashes and test results.
- Run the complete workflow from clean inputs.
- Record both positive and negative outcomes.
- Prepare a five-minute walkthrough: current position → what will run out → what may expire → action this week → why it is safe.
- Audit every public claim against the frozen evidence.

### Gate

- Clean run and full test suite pass.
- All three case paths are visible and inspectable.
- A sales walkthrough uses no unsupported result.
- A distributor-aware reviewer recognises the decision and can name what they would need to pilot it.

### Stop

Do not release if only the positive path is polished, if the controls are hidden, or if the language implies client savings or guaranteed waste prevention.

## Current next step

Plan Phase 1 in full: the exact hand-calculated products, lots, dates, supplier terms, demand views, three case facts, expected outcomes and independent-review method. Only then may synthetic records be generated.
