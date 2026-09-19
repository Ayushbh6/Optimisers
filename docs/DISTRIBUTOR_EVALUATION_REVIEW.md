# Distributor ordering implementation — evaluation review

Status: **candidate failed the frozen release gate on 15 September 2026. The full client demo is not ready.** Engine and evaluation work are retained; UI, API, local CSV import and container delivery are paused at the approved stop condition.

## Frozen evaluation result

All 30 reserved cases completed, following all 18 development cases. **Zero families qualified; two non-ample families were required.** Only two individual restricted-spending cases met an improvement route and the expiry/ending-stock checks. That family needed four of five cases, not two.

| Scenario family | Individual cases meeting thresholds | On-time unit service change, percentage points |
|---|---:|---:|
| Ordinary trading | 0/5 | -4.52 to +0.76 |
| Restricted spending | 2/5 | -5.08 to +6.76 |
| Supplier disruption | 0/5 | -3.18 to +0.50 |
| Demand changes | 0/5 | -0.90 to +0.04 |
| Ageing stock | 0/5 | -3.46 to +0.00 |
| Ample stock (control) | 0/5 | -6.60 to +0.68 |

Two cases crossed the five-point regression block: restricted spending, seed 5505 (**−5.08 points**), and ample stock, seed 7707 (**−6.60 points**). Complete-line service also declined by more than one point on average in ageing and ample-stock cases. Every paired result is retained; the positive restricted-spending example cannot support a general improvement headline.

The candidate sometimes reduced stock but did not reliably protect realised service. Matching the comparison's projected service was insufficient. Handling uncertainty and maintaining useful stock buffers warrant diagnosis; these results alone do not establish a single root cause. **This rejects the current candidate's release claim, not the dataset or the purchasing problem.**

The extra two-day supplier-delay and 30-day freshness evaluations were **not run**, because the nominal gate already failed. They are not described as passed or failed. No scenarios, acceptance thresholds or numerical methods were changed after reserved outcomes were opened. A revised method requires a new documented evaluation version; these 30 cases are now known and cannot be reused as an unseen test set.

![All 30 reserved cases](../artifacts/distributor-demo/reserved-evaluation-v1/tradeoffs.png)

## Final audit and retained work

All 60 saved policy action histories reproduced their reported outcomes and reconciled stock, spending, customer and supplier obligations with zero errors. This audit replays saved actions through the shared physical engine; it is not a second independent simulator. Carry-in customer obligations are reported separately for every case. Source hashes still match the frozen contract and retained v2 dataset.

Task-created database copies, test outputs, the plot cache and the interrupted preliminary batch were removed after verification. Regeneration configurations, source/database hashes, all completed decision reports, comparison tuning evidence, the plot and audits are retained inside the repository. The original demonstration database remains intact.

The public purchasing UI, FastAPI service, local import/correction workflow, exports, browser/accessibility checks, five-session load test and deployment container are **not implemented**. Solver work is bounded, but the proposed interactive latency targets have not been certified. Work stopped before those stages as the approved plan requires. No external deployment or client outreach occurred.

## What is implemented

The independent replenishment package contains public operational state, dated lot accounting, request-based forecasts, a budget-aware stock-cover comparison, a 28-day case-order model, independent operational replay, validation, and a private evaluation harness. The website, local CSV import workflow and deployment package remain behind the approved value gate.

The approved delivery contract is [DISTRIBUTOR_IMPLEMENTATION_PLAN.md](DISTRIBUTOR_IMPLEMENTATION_PLAN.md). The original retail plan and retained v2 dataset are unchanged.

## How the comparison works

Both methods see the same recorded requests and forecast. The shared forecast was selected from four-week average, eight-week average and weekday-adjusted eight-week average, using eight completed historical weeks. The selected method is the eight-week average. The comparison uses zero additional safety days: across development cases it was within one service percentage point of the best tested safety setting, with less stock investment.

Each method evolves its own inventory and supplier commitments for eight future weeks. Both use the same supplier/date conditions, customer requests, physical dispatch rules and accounting. A further 30 days resolve outstanding obligations without new requests or purchases; this settlement period is reported separately.

Service means **units dispatched by the requested date**. Outbound transport is not modelled, so these figures must not be presented as proof of delivery to a customer's premises. Complete-line service is reported separately from unit service. Money is stock valued at acquisition cost plus undelivered purchase commitments; this is not profit or bank cash savings.

## Planning assumptions and limits

- Projected demand cohorts are estimates, not predictions of named future customer orders. Historical customer shares allocate these cohorts; real booked lines remain unchanged.
- Future supplier arrivals use normal terms and latest released notices. A late order without a reliable new date cannot support promised coverage. Historical supplier-delay distributions are not estimated in this version.
- Unknown incoming freshness is modelled as 60 days remaining on arrival. This is an illustrative conservative assumption, not a recorded supplier guarantee.
- The case-order model relaxes allocation of estimated future demand. Every proposal is replayed through actual due-date, freshness, whole-line and earliest-expiry dispatch. Only replayed service and investment can support selection. One bounded projected-target correction is permitted; no future outcomes enter it.
- The recommendation must match the comparison's projected on-time service and booked-unit fulfilment before a lower-investment alternative replaces it. This is a projection condition, not a guarantee under uncertain future demand.
- Runtime is bounded; solver status and rejected alternatives remain recorded. Mathematical optimality, where reported, concerns the primary planning model. It is not global optimality for a real business.
- No selling prices, margins, customer lifetime values or invented shortage penalties are used. The objective is unit service and stock investment, not profit maximisation.
- Customer requests are external to the policy: poor service does not change subsequent requests in this constructed business. Customer retention and payment timing are not modelled.
- The frozen primary service cohort contains requests created during the eight future weeks. A separate action-replay audit reports obligations carried in from history, without changing that cohort or the gate after results are opened.

## Verification and corrections before freeze

113 repository tests passed before reserved generation. These include hand calculations, quantity and spending reconciliation, customer rules, supplier notice timing, no future request leakage, independent supplier/date responses, invalid inputs, and release-gate logic. The new evaluator materialiser reproduces the original v2 database's logical records exactly on a development seed.

An initial historical backtest omitted the last completed week. This was corrected before freezing; the selected forecasting method remained unchanged. The interrupted preliminary optimiser batch is not evaluation evidence. The completed development run uses the corrected code. The corrected forecast report's per-history array follows alphabetically sorted development case-folder names.

A repeated check on the active purchasing decision for restricted-spending development seed 2202, 7 July 2025, selected identical complete logical purchase schedules on two fresh solves. This is a checked example, not a guarantee that time-limited solves are identical across hardware or workloads. Retained action journals make completed evaluation outcomes auditable.

## Evidence locations

- `artifacts/distributor-demo/implementation-development-v1/`: comparison selection, completed development cases, test verification, environment and frozen contract.
- `artifacts/distributor-demo/reserved-evaluation-v1/`: all 30 paired results, failed release-gate decision, action-replay audits, regeneration records and comparison plot.

The frozen source hashes, settings and thresholds must remain unchanged after reserved data are opened. No positive headline or UI release is authorised by correctness checks alone.
