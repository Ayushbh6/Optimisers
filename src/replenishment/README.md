# Distributor replenishment engine

This is an implementation and evaluation package, not a released web demo.
The frozen v1 candidate failed the 30-case reserved release gate: zero qualifying
families and two service regressions above five percentage points. Product UI,
API, imports and deployment remain paused under the approved stop condition.
Read `docs/DISTRIBUTOR_IMPLEMENTATION_PLAN.md` and
`docs/DISTRIBUTOR_EVALUATION_REVIEW.md` before extending it.

## Information boundary

Released records → `PlanningSnapshot` → forecast and purchase alternatives →
independent physical replay → checked proposal.

`contracts`, `validation`, `forecast`, `baseline`, `discrete`, `projection` and
`planner` are planning code. They receive no future-event connection, scenario
seed or latent generation settings. `state.load_snapshot` loads a historical
end-of-day anchor; advance the operational day and release that day's records
before requesting an ordering decision.

`evaluator.World`, `scenarios`, `batch` and `src.evaluate_distributor` are private
evaluation tooling. Do not expose their databases or interfaces to a public
planning service. Both evaluated policies use `physical.Operations`, with the
same expiry, receipt, dispatch, cancellation and accounting rules.

## Public Python interface

`plan(PlanRequest(snapshot, settings, locks, excluded))` returns `PlanResult`.
Its alternatives contain dated proposed purchases over 28 days, conditional
metrics, status and explanations. Only today's purchases are committed during
evaluation. No API in this package emails or submits a supplier order.

Money is integer euro cents. Quantities are integer individual sale units;
purchase quantities must be whole cases. Dates are calendar dates. The caller
owns the explicit before-ordering decision boundary. Service measures dispatch
by the requested date; outbound transport is outside this model.

The active planner does not use the mathematical allocation model to choose a
purchase. It generates a bounded set of whole-case edits around stock cover and
lets exact warehouse replay accept or reject each basket. The older solver and
joint-model modules remain as retained negative research paths; they are not the
recommendation path.

## Commands

Run from the repository root with `.venv/bin/python`:

```sh
.venv/bin/python -m src.replenishment.cli development --baseline-only --output artifacts/distributor-demo/NEW-DEVELOPMENT-RUN
.venv/bin/python -m src.replenishment.batch --development artifacts/distributor-demo/NEW-DEVELOPMENT-RUN --workers 4
.venv/bin/python -m src.evaluate_distributor verify --development artifacts/distributor-demo/NEW-DEVELOPMENT-RUN
.venv/bin/python -m src.evaluate_distributor freeze --development artifacts/distributor-demo/NEW-DEVELOPMENT-RUN --output artifacts/distributor-demo/NEW-DEVELOPMENT-RUN/frozen-evaluation.json
.venv/bin/python -m src.evaluate_distributor reserved --freeze artifacts/distributor-demo/NEW-DEVELOPMENT-RUN/frozen-evaluation.json --output artifacts/distributor-demo/NEW-RESERVED-REPRODUCTION --workers 4
```

Existing runs are not silently replaced. The last command reproduces already
opened reserved seeds; it does **not** create a new independent holdout. A changed
numerical implementation requires a new evaluation version and an explicitly
declared new evaluation set. Do not use previously opened outcomes for tuning
and then call the same cases unseen.

The release gate is a business acceptance check, separate from correctness
tests. Passing ledger tests does not establish savings or readiness to sell.

Current v4 development challenges every candidate under nominal, lower, higher
and four historical request patterns. Future stock-cover decisions are
recalculated from each replay's evolving physical state. These are stress views, not
confidence intervals. The first four-case repeated trial found one small
ample-stock service regression, so the 18-case batch remains blocked. See
`docs/DISTRIBUTOR_DISCRETE_TRIAL_01.md`.
