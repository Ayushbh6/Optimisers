# Credible demonstration data: agreed direction and proposed first demo

## Agreed direction — 14 September 2026

The user approved clearly labelled, self-created demonstration data as the main route to working website demos. A perfect public dataset is no longer a prerequisite. The core acceptance criterion is **client showcase worthiness: a useful capability addressing a problem a real business could pay to solve**, not an attractive chart or a favourable simulated percentage.

The database foundation for the first demo is now implemented and documented in [DISTRIBUTOR_DEMO_DATA.md](DISTRIBUTOR_DEMO_DATA.md). The optimiser, evaluation experiment and website remain separate work.

Read this with [TARGET_CLIENTS.md](TARGET_CLIENTS.md). First two demos must fit Lona/Matt Import distribution or Perwanger manufacturing/material planning. Contacts are not clients; willingness to pay and their actual workflows remain unverified. Start with one demo. Do not stretch it to represent all three firms.

This direction supersedes the requirement to find public operational records before designing the next demo. Keep PLAN_phase_2.md and the archive unchanged as the original retail investigation contract. Previous dataset audits remain valid for the historical claims they assessed; those limitations do not rule out a transparent constructed demonstration.

## What establishes credibility

Business decision → explicit example records and assumptions → working recommendations → inspectable consequences and limitations.

- **Honest:** synthetic records are labelled throughout the interface, downloads and case study. No named prospect data, implied engagement, hidden future information or guaranteed savings.
- **Valuable:** show what to order, when, why, and which shortages cannot be avoided. Measure budget use, fulfilment, stock exposure and ordering workload separately.
- **Real-world standard:** use coherent stock/order records and relevant operating constraints. Commercial demonstration practice supports the format, not the realism of our chosen numbers.
- **Sellable:** recommendations must survive changed inputs, explain trade-offs and produce a usable order proposal. A working solver alone does not establish demand for a product.

Commercial evidence checked 14 September 2026: [Streamline](https://gmdhsoftware.com/documentation-sl/basic-workflows) demonstrates inventory ordering using QuickBooks sample data. [SkyPlanner](https://skyplanner.ai/trial/) offers ready-made example data and adjustable production schedules. These establish commercial use of example-data demos, not a universal certification or proof of how every startup began.

Example data can demonstrate decision-making under stated conditions. It cannot establish real-world forecasting accuracy, achieved customer savings or willingness to pay. Never describe a synthetic performance result as a historical business result.

## Demo 1 direction: weekly supplier ordering for a food distributor

**User:** the person deciding supplier orders, with an owner or finance manager approving stock expenditure.

**Decision:** what quantities to order this week to cover due customer orders and expected sales, within available cash and supplier rules.

**Why a buyer might care:** missed orders harm service; unnecessary stock consumes cash and may expire; checking many products manually takes effort. The demo should turn these competing needs into an editable order proposal, with reasons and unresolved risks. These are value hypotheses, not confirmed problems at the contacts.

Proposed starting size: one warehouse, 30 fictional packaged-food products, four suppliers, 26 weeks of generated prior activity and an eight-week planning/evaluation horizon. These are manageable design choices, not estimates of the target firms. Use generic fictional names and euros. Include fast sellers, intermittent sellers and slow stock without assuming their exact real-world proportions.

Keep the initial workflow focused. Exclude routing, markdown response, production, supplier negotiation and multi-warehouse transfers. Perwanger warrants a separate production/material-planning design later.

## How to create coherent records

Generate a small fictional business through events, rather than independently randomising spreadsheet columns. Use simple declared historical ordering rules to create its history; do not create an absurdly poor starting business to make improvement easy.

| Record | Essential contents and purpose |
|---|---|
| Products | Product/unit identity, case size, purchase cost, selling price, storage size and shelf-life rules. All quantities reconcile in base units. |
| Supplier terms | Eligible products, order days, minimum quantities/order values, expected delivery times, charges and effective dates. |
| Customer orders | Creation/availability time, requested product and quantity, due date, fulfilment and any remaining or cancelled quantity. |
| Stock lots | Opening quantity, receipt date, expiry date and reserved quantity; no unexplained negative or disappearing stock. |
| Supplier orders and receipts | Placement, expected arrival, notification time, actual arrival, quantity and lot identity; partial/late deliveries are explicit. |
| Stock movements | Receipts, fulfilment, expiry and justified adjustments, linked to source records. |
| Planning settings | Spending limit, storage limit, service priorities and treatment of unmet orders; all visible and adjustable. |
| Scenario manifest | Generation rules, seeds, units, assumptions, source rationale, version and development/evaluation assignment. |

Generate history from explicit opening lots and outstanding orders. Reconcile each lot from opening stock through movements to closing stock. Distinguish new-order budget from cash already committed to outstanding orders. Define the event order within each day before generation so arrivals cannot fulfil an earlier dispatch retroactively.

Choose ranges before seeing optimiser results. For each parameter, record a public operational source where available, or label it an illustrative design assumption; explain its range and what changing it might affect. Do not call assumptions representative industry statistics. Review relationships too: supplier-wide delays affect related products together, promotions affect relevant products, and lot expiry follows actual receipt timing.

Start with valid operational records. Separately include a small, labelled set of input errors (missing cost, duplicate order, inconsistent units) to test clear rejection or warnings. Do not silently repair them or mix import defects into performance comparisons.

## Scenario coverage: ordinary operation as well as difficulties

Freeze these families before generating results:

1. Ordinary replenishment with adequate cash and reliable supply.
2. Tight cash forcing a choice between products; include a realistic shortage that no ordering policy can avoid.
3. Supplier delay and partial delivery, with notification becoming available at a declared time.
4. Uneven customer orders and a pre-announced promotion; also an unannounced increase that the planner cannot foresee.
5. Slow stock approaching expiry alongside products needing replenishment.
6. Ample existing stock, where ordering nothing or matching a simple rule is appropriate.

Include differences in initial stock health, rather than making every scenario severely overstocked or understocked. Scenario frequencies are test coverage, not claims about how often events occur in real firms.

## Fair evaluation plan — define before running

First test one decision date using customer orders already received. This isolates whether the planner respects constraints and makes defensible trade-offs without requiring a forecasting claim. Then, if worthwhile, test repeated weekly decisions with uncertain future orders.

For the repeated test, the evaluator may hold future customer requests and delivery outcomes; the planner receives only records available at its decision time. It must not receive future random seeds, hidden generation parameters, future orders or actual arrival dates before notification. Forecasts, if needed, use past available records and are identical across ordering methods initially. This keeps ordering skill separate from forecasting skill.

Compare with a competent, documented stock-cover ordering rule that accounts for pending orders, case sizes, supplier minimums and the same cash/storage limits. Specify how it prioritises products when cash is insufficient. Give both methods equal development effort and freeze their settings. Do not choose a deliberately weak baseline or compare only against our old unsuccessful policy.

Both methods face the same external customer requests and supplier conditions, with delivery outcomes linked consistently to supplier/date events rather than random-call order. They share opening positions and accounting rules. Each method develops its own stock and observed fulfilment history. Do not give one method the other method's future observations.

Use three declared development seeds and five untouched evaluation seeds for each of the six families: 18 development and 30 evaluation scenarios. This is a proposed bounded coverage set, not evidence of statistical representativeness. Freeze the generator, parameter ranges, methods and measurement definitions before opening evaluation results. Any later revision creates a new version; disclose previous outcomes and use new evaluation cases. Never keep regenerating until a win appears.

Report due-order fulfilment, late/unfilled quantities, ordering spend and charges, average stock at purchase cost, expiry write-offs, ending usable stock and outstanding commitments. Carry outstanding orders and remaining obligations through the reporting boundary; do not reward postponing costs beyond the end. Do not equate lower purchase spending with profit or use invented shortage penalties to manufacture savings.

## Proposed showcase gates

These are product review gates, not tests that force a favourable numerical result:

- **Correctness:** zero unexplained stock-balance errors or hard-constraint breaches across valid scenarios. Infeasible service requests and invalid inputs produce an explicit explanation.
- **Decision value:** demonstrate a useful improvement against the competent baseline on the frozen evaluation set, with all scenario outcomes and regressions shown. Specify a minimum worthwhile trade-off in units/euros and fulfilment terms before running; no universal savings percentage is justified yet.
- **Robustness:** compare across all six families and reasonable changes to the two assumptions most likely to reverse the conclusion. A selected attractive example cannot stand in for the full evaluation.
- **Usability:** a viewer can change a budget or supplier delay, see a recalculated proposal, understand a changed decision and export the proposed order lines. Proposed target: response within five seconds at this small scale, measured on a declared environment.
- **Buyer relevance:** an external reviewer familiar with distribution can recognise the decision and identify how the proposal would enter their work. For commercial validation, look for a specific next step such as a request to explore a scoped pilot; praise or a technically correct demo does not prove willingness to pay. Seeking contact or sending anything requires user authorisation.

Do not declare the demo showcase-ready if only correctness passes. Stop or narrow the design if simple ordering is just as useful, improvement requires implausible assumptions, the important constraints cannot be explained, or a knowledgeable reviewer identifies a missing condition that changes the decisions.

## Next step and storage

The database specification, exact fields and generation rules are now fixed in [DISTRIBUTOR_DEMO_DATA.md](DISTRIBUTOR_DEMO_DATA.md). The next separate decision is the optimiser experiment: freeze its competent comparison rule, objective priorities and numerical business acceptance criteria before opening the reserved evaluation scenarios.

Keep the specification in this document or one linked final document; future data and compact evidence belong under a single repository-local demo folder. Retain configuration, reproducible generation code, final example records and evaluation summaries. Remove only task-created intermediate outputs after verification. Do not create system temporary folders, buy data, restart broad public-dataset hunting or rebuild Part 1 as a prerequisite.
