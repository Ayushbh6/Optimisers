# Synthetic distributor database specification

**Reviewed version: distributor-demo-v2.** The corrections and final evidence are in [DISTRIBUTOR_DATA_REVIEW.md](DISTRIBUTOR_DATA_REVIEW.md). Regenerate v1 files; do not mix versions.

## Purpose and claim boundary

This database supports a future working demonstration of weekly stock ordering for a packaged-food distributor. It represents one fictional warehouse with 30 products, four suppliers and 20 business customers.

> **SYNTHETIC DEMONSTRATION DATA — NOT CLIENT RECORDS**

It can show that software respects the represented orders, stock lots, expiry terms, supplier restrictions, capacity and spending limits. It cannot establish historical client savings, real-world forecast accuracy or customer willingness to pay.

## Time and information boundary

- Historical activity: 6 January–6 July 2025, exactly 26 weeks.
- Reserved future: 7 July–31 August 2025, exactly eight weeks.
- Dates are calendar dates. Receiving and dispatch happen Monday–Friday; expiry happens every day. Public holidays are outside version one.
- Every operational event records its event date and when it became known.
- `operational.sqlite` contains the fictional history and dated information visible to a planner.
- `evaluator.sqlite` contains future customer requests and date-based supplier conditions. It must never be passed to a planner.
- `snapshot(as_of)` and `export_csv(as_of)` default to end-of-day knowledge. Set `phase="before_ordering"` to include that day's arrivals and customer requests while excluding its later supplier orders, dispatch and cancellation. Dates outside the historical interval are rejected.
- Supplier status, received quantities and outstanding customer/supplier quantities are derived at the cutoff. Raw supplier `status` means placement state and remains `open`; it is not a mutable current status.
- Exact demand-generation classes and promotion effects are absent from operational tables. The regeneration configuration is evaluator material, not a planner input. Every CSV export carries a synthetic-data manifest; empty tables retain headers.

Daily processing order:

```text
expiry → supplier notices and receipts → new customer orders
→ scheduled ordering decision → customer dispatch
→ overdue cancellation → closing balances
```

## Data dictionary

All monetary values are integer euro cents. All product quantities are integer individual sale units. Supplier-order quantities must be complete cases and meet the product minimum.

| Table | Grain and important fields |
|---|---|
| `suppliers` | One supplier: ordering weekday, minimum merchandise value, delivery charge and normal lead time. |
| `products` | One product: fictional name, correct food category, case size, storage volume and normal shelf life. Demand coverage classes exist only inside the generator. |
| `supplier_product_terms` | One dated supplier/product term: purchase cost and product minimum order. |
| `customers` | One customer: size, partial-delivery permission, maximum lateness and required remaining shelf life. |
| `planning_limits` | One dated warehouse plan: weekly new-order spending limit and physical capacity. |
| `promotions` | One product event: announcement and active dates. Included only in the demand-change scenario; the actual generated effect is hidden. |
| `customer_orders` | One customer order with creation and due dates. |
| `customer_order_lines` | One requested product and quantity within an order. |
| `supplier_orders` | One placed order: supplier, original expected arrival, delivery charge and immutable placement status. Use snapshots for status at another date. |
| `supplier_order_lines` | One ordered product, whole-unit quantity and agreed unit cost. |
| `supplier_updates` | One immutable notice of delay, partial delivery, cancellation or capacity rejection. |
| `receipts` | One arrival against one supplier-order line, including quantity refused for lack of capacity. |
| `stock_lots` | One traceable lot with receipt link, acquisition cost and expiry date. Opening lots have no receipt link. |
| `shipments` | One allocation from one eligible stock lot to one customer-order line. |
| `cancellations` | One explicit unfilled customer quantity and reason. |
| `stock_movements` | One opening, receipt, shipment or expiry quantity change linked to its source. |
| `closing_stock` | Derived history-end quantity for each lot, used for independent reconciliation. |
| `dataset_manifest` | Version, dates and synthetic warning. Generation seeds and evaluator hashes are absent, so changing future events cannot alter this database. |

Evaluator-only tables contain future customer-order headers and lines plus supplier/date conditions expressed as delay workdays and fill-rate basis points. Look up supply conditions using the original expected arrival date; order identifiers and execution order do not affect them. The condition table includes a 30-calendar-day tail beyond the final demand date.

Two continuation tables preserve exact pending deliveries and unreleased notices for orders already placed during the history. Their quantities must equal historical ordered quantities minus receipts. These continuations are evaluator-only: snapshots expose the originally expected arrival and any notices already released, never the hidden actual arrival. Future policy orders use `supply_condition` with new order quantities; they must not copy the historical policy's receipts.

## Generation design

Ten products are assigned to each coverage class: fast, moderate and intermittent. This is scenario coverage, not a claimed market mix. Customers have different sizes and stable product preferences. Each weekday, the generator first determines whether a customer requests a preferred product and then generates a positive quantity. Product-category changes are shared, so related series are not artificially independent.

The historical ordering rule reviews each supplier on its declared weekday. It uses confirmed ordered quantities less receipts, known due orders and the previous 28 calendar days of requested units. For each date through expected receipt plus seven calendar days, it takes the greater of known due orders and the recent daily average, then sums the daily requirements. Working-day lead times are converted to actual dates before computing the horizon. Stock must meet the strictest customer shelf-life rule at the expected receipt date to count toward the target. This conservative simplification may over-order for more flexible customers and is explicitly not claimed optimal.

The rule rounds to cases, respects minimums and prioritises imminent shortages before low stock coverage under the weekly spending limit. Expiry is fixed at the original expected arrival plus normal shelf life minus 14 days. A delay or capacity retry cannot make food younger. Capacity-rejected quantities remain outstanding and retry on the next working day.

This rule is used only to build a believable connected history. Future optimiser testing must define a competent comparison separately and cannot claim that this history rule represents a real client.

## Declared scenario coverage

The development suite contains three predeclared seeds for each of six families: ordinary trading, restricted spending, supplier disruption, demand changes, ageing stock and ample stock. Five additional seeds per family are reserved and cannot be generated by the development command.

Supplier disruptions are date/supplier conditions rather than receipts prewritten for one policy. Demand changes distinguish a promotion announced to the planner from a later category increase the planner cannot foresee; these increase positive order quantities without also multiplying occurrence probability. The ample-stock family has a declared five-week stock-cover campaign in the final six history weeks, to preserve the ample-stock condition at the demonstration boundary. Ageing stock begins with extra slow lots and mixed remaining shelf life, some extending near the boundary. Actual near-expiry quantities are reported for every seed, including cases where the effect is weak.

Numerical ranges and their effects are recorded in `assumption_register.json`; the fixed demand, supply and history recipe is in `regeneration_config.json`. Source hashes in the run and suite manifests identify the implementation. These are illustrative inputs, not industry statistics. No held-out optimiser comparison has been run, and the historical fulfilment percentages must not be marketed as savings.

## Completion checks

The audit independently checks foreign keys, SQLite integrity, stock conservation, non-negative lot balances, customer and supplier quantity reconciliation, expiry eligibility, customer delivery rules, case sizes, product and supplier minimums, weekly spending, warehouse capacity, integer units/money and knowledge dates. It also reconstructs expected movements from receipts/shipments, replays earliest-expiry allocation, requires a complete closing ledger, validates cancellation deadlines and reconciles evaluator continuations. SQLite STRICT tables reject fractional stock and null keys. Invalid unit, missing cost and duplicate-key fixtures are rejected.

The reader and auditor open SQLite in read-only mode. Generation and export reject output paths outside `artifacts/distributor-demo/`, including symlink escapes, and refuse replacement. Failed runs preserve diagnostics; successful suite runs keep hashes, configurations and all check outcomes while removing their intermediate databases.

The retained development suite reports every scenario, including weak fulfilment and high-expiry cases. No test requires savings, an optimiser win or an attractive percentage.
