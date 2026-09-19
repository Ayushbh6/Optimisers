# Wholesale dataset audit: initial client-demo verdict

13 September 2026. **Do not build either of the first two flagship optimisation demos on this dataset in its present form.** It is credible enough to explore and useful for demonstrating transactional analysis, but it cannot currently support a defensible improvement in stock or purchasing decisions. This is an evidence decision, not rejection of Kaggle.

Source: [Underwear Data with 11 Tables & up to 100K+ rows](https://www.kaggle.com/datasets/hserdaraltan/underwear-data-with-11-tables-and-up-to-100k-rows). Target context: [TARGET_CLIENTS.md](TARGET_CLIENTS.md).

## What was audited

Read all eleven CSV tables from the public archive in memory. Rechecked the publisher's provenance and licence metadata. Checked identifiers, relationships, quantities, date order, product histories and whether a basic incoming-minus-outgoing calculation could support further stock reconstruction. No records were repaired, no optimiser was built, and no policies or forecasting methods were tested.

Audit code and numerical evidence: `artifacts/dataset-search/wholesale-audit/audit.py` and `audit.json`. Reproduce with `python3 -B artifacts/dataset-search/wholesale-audit/audit.py`. The archive hash matches the earlier inspection. No raw archive or customer/employee data was retained.

## What is genuinely useful

- 105,757 sales lines, 2,286 sales orders, 20,951 inventory transactions, 232 purchase orders and 4,183 products.
- No duplicate primary identifiers in any table. All sales lines join to products and orders; inventory products and nonblank purchase references also join correctly.
- Sales order dates cover 34 calendar months, July 2003–April 2006. Sales quantities and prices are populated throughout. Zero quantities/prices remain visible rather than being discarded.
- Product attributes identify sizes, fabrics and pack sizes; quantities refer to either dozens or single units. Raw quantities across these two pack types must not be labelled as a common physical-unit total.
- Publisher states a real wholesale-company origin and declares CC BY-SA 4.0. Translation, correction, anonymisation and partial imputation are disclosed. There is no independent named-company confirmation or field-level imputation record.

These are useful inputs for customer/product sales analysis and purchase-history reporting. They are richer than a typical flat sales file.

## What prevents an honest inventory improvement claim

| Finding | Business implication |
|---|---|
| 17,446 of 17,606 dated inventory rows linked to purchase orders have exactly the same date as the order: 99.1%. | These could be posting dates or genuinely same-day events. They are not independently established receipt times. A calculated zero-day supplier lead time would be unjustified. |
| 18,717 of 18,724 rows containing both ordered and received quantities show equal values. | These may be final order/receipt summaries. They do not establish when partial deliveries or shortages occurred. |
| 3,345 inventory rows lack purchase references. | Some may represent starting stock or adjustments; the published schema does not establish which. Do not delete them or automatically classify them as opening inventory. |
| 1,151 inventory rows lack unit purchase prices; 32 have an ordered quantity but no received quantity. | Missing costs and unresolved receipts cannot silently become zero or completed orders. |
| 12 orders ship before their order dates, affecting 415 sales lines; the worst gap is 1,096 days. | Shipment chronology needs explanation. The remaining 2,271 same-day and 3 next-day orders also give little evidence about fulfilment delays. |
| No independently identified opening/closing on-hand quantity snapshots. | There is no anchor against which to verify reconstructed stock. A product's InventoryDate is not a stock quantity. |
| 2,180 products carry an undated “Out of Production” status. | This cannot be used to stop past orders unless the historical effective date is known. |
| No stockout, unfulfilled-customer-demand or expiry-batch records. | Sales are not verified total demand; the data cannot prove maintained service or food-waste savings. |

### Stock-flow diagnostic, not reconstructed historical stock

As a diagnostic only, start at zero, add recorded received quantities, subtract recorded missing quantities and sales, and net movements by day. Blank movement cells are treated as no movement **only within this diagnostic**. One undated inventory record cannot enter the timeline. These assumptions are unverified; the calculation is deliberately not presented as stock truth.

- Using sales order dates, **1,010 of 4,157 represented products (24.3%)** go negative at least once. These products account for **41,466 sales lines (39.2%)**.
- Using shipment dates, **1,139 products** go negative. The outcome is therefore sensitive to transaction timing, but the 12 invalid shipment dates are not the whole problem.
- Both variants end negative for **98 products**; ending counts agree because shifting sales dates does not change total movement quantities.

Negative values do not prove fabricated data or actual negative physical stock. They show that this straightforward interpretation lacks opening balances, complete movements or correct event semantics. Filling the gaps with the minimum stock needed to eliminate deficits would use future sales and cannot establish real starting stock.

## Four-gate judgment

| Gate | Judgment for a flagship inventory optimiser |
|---|---|
| Honest | Fails for the proposed savings/service claim: inventory and lead-time history are not established. Passes only for narrower observed-transaction facts, with provenance caveats. |
| Valuable | The decision is valuable: a wholesale buyer cares about availability, cash tied up in stock and supplier purchasing. This dataset has not demonstrated those outcomes. |
| Real-world standard | The table structure resembles real operational inputs, but a credible implementation must establish stock state and receipt timing before issuing or evaluating purchase recommendations. |
| Sellable | Not yet suitable for either priority demo. A buyer could reasonably ask how stock, receipt dates and avoided shortages were verified; we could not give a supported answer. |

[Lokad's inventory documentation](https://www.lokad.com/inventory-optimization/) describes combining incoming/outgoing records and forecasting relevant uncertainties. Its [lead-time documentation](https://docs.lokad.com/legacy/calculating-the-lead-times/) distinguishes purchase orders from deliveries. The issue here is not that imperfect data is unusual; it is that we cannot resolve these specific meanings from the public release.

## Could a narrower demo still be useful?

Yes: customer/product order trends, repeat purchasing, product-family sales forecasts or a data-readiness audit. But there are only a median of 13 sales lines per sold product across the period, so product-level forecasting is not automatically strong. Family grouping is a possible future experiment, not a result already earned.

A data-readiness workflow could show integration and validation skill. It would not demonstrate the optimisation skill the first two demos are meant to sell. A purchase or replenishment simulation with invented lead times, starting stock and costs would make the main result depend on assumptions again.

Matt's non-food wholesale activity is the closest business analogue; Lona's food distribution is less direct. There are no production processes or material-conversion records to support Perwanger's manufacturing decisions. Data age is a presentation limitation, but it is not the principal rejection reason.

**Verdict: reject this dataset for the current flagship inventory-optimisation demo. Retain only the compact audit.** This is not proof that every narrow use is impossible. Reconsider only if published documentation establishes movement timing, stock anchors and what was imputed; it is not a request for the user to obtain inaccessible company records. No monetary savings, maintained availability or optimised buying claim is justified by this audit.
