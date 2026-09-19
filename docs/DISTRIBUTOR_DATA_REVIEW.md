# Distributor dataset review and corrected release

## Verdict

The corrected **distributor-demo-v2** data is ready as input to the planned demonstration. It supports traceable stock-ordering examples and fair development work. It is still a small fictional operation, not a verified model of the target firms or evidence of commercial savings.

The previous 65-test / 16-audit-check sign-off was insufficient: it missed future-information exposure and record-consistency defects. This review fixes those defects and adds regression tests that reproduce them. No optimiser has been built or selected, and no reserved evaluation seed has been generated.

## Material findings and fixes

| Finding in v1 | Correction |
|---|---|
| Opening-date snapshots exposed a PO's later receipt status. | Derive status and open quantities from records known at the selected cutoff. |
| 21 fully received orders in the retained example were marked partially received because joins double-counted ordered quantities. | Aggregate each order line once; keep placement records immutable. |
| Four future notices were stored in the operational database. | Release notices chronologically; keep unannounced notices in evaluator-only continuation records. |
| Pending supplier orders lacked complete evaluator continuations. | Preserve scheduled remaining quantities and original expiry; independently reconcile them to outstanding orders. |
| Warehouse-rejected quantities disappeared from the engine's pending schedule. | Retain them and retry without resetting expiry. |
| Random supply used PO identifiers, and future supply differed from historical supply rules. | One supplier/date-based response shared across history and future conditions. |
| Product names and categories were mismatched. | Use the intended confectionery, snack and dry-grocery groupings. |
| All scenarios advertised a promotion, even where none affected demand. | Limit the announcement to the demand-change family; hide the actual generation multiplier. |
| Working-day lead times were combined with calendar-day averages inconsistently. | Build an actual calendar horizon and avoid double-counting each day's booked demand. |
| The ample-stock condition largely disappeared before the intended demonstration date. | Declare a stock-building campaign in the history; show its costs and stock exposure. |
| Several tests repeated the generator's own totals and did not detect missing source records. | Add independent source-to-ledger checks, corrupt-record tests and a hand-calculated fulfilment/expiry example. |

These are correctness and scenario-coverage changes. The generated history changed; v1 and v2 fulfilment percentages are not a before/after optimiser comparison.

## Retained evidence and use

Final verification: **82 repository tests passed (including 28 distributor tests)**; all **22** audit checks passed for the default; all **18** development scenarios passed. Data/source hashes match, and the retained default SQLite files exactly reproduce the corresponding independently generated suite case. The final default has 7,594 historical requested units, 7,068 eventually shipped, 6,676 shipped on time, 453 cancelled, and 73 still open. It retains 1,291 stock units, 206 expiring within 30 days, and 336 outstanding supplier units. These are scenario results, not optimisation gains.

- `artifacts/distributor-demo/default/`: the supplier-disruption example, two SQLite files, audit, configuration, source/data hashes, coverage and linked-record walkthrough.
- `artifacts/distributor-demo/development-suite/`: all 18 scenario outcomes and audit results, their configurations and database hashes. Five seeds per family remain reserved.
- Use `snapshot(..., phase="before_ordering")` to prepare a decision using that day's arrivals and booked orders. Default snapshots show end-of-day state.
- Keep evaluator files, regeneration rules and reserved scenario material outside any client-facing planner process.

The final default contains 30 products, four suppliers and 20 customers, with 26 historical weeks and eight weeks of future customer requests. The audit reports due-date fulfilment separately from eventual fulfilment, expiry write-offs at acquisition cost, remaining stock value and outstanding supplier commitments.

## Practical limitations

- Demand patterns, lead times, customer terms, budgets and storage volumes are illustrative choices, not estimates of a named prospect's operations.
- The small catalog demonstrates connected decisions, not production-scale performance.
- The historical rule is conservative and simple. It is not a qualified future comparison baseline; choosing that baseline remains part of the optimiser experiment.
- Customer partial-delivery permission operates per product line, not across an entire mixed-product order. There is no substitution, returns, customer credit, VAT, transport routing or cold chain.
- Data integrity and tested information boundaries establish readiness for development. Buyer interest and measurable optimisation value still require their own evidence.
