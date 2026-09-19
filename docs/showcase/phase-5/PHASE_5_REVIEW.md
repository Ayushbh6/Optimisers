# Phase 5 — Explanation and supplier export review

**Technical gate: PASS — 18 September 2026.**

One decision object now drives the buyer comparison, product changes, cash, expected arrival, delivery protection, expiry, ending stock plus commitments, rejected-risk examples and supplier CSV. The CSV repeats the decision hash on every line and is labelled synthetic.

The positive explanation names the exact change:

- Tomato Soup: five to eight cases to restore the supplier minimum with a product already needed.
- Honey Drops: one to zero cases because the top-up is unnecessary for booked deliveries.
- Cash: €620.00 to €524.00, including the unchanged €20.00 delivery charge.
- Arrival: 22 September 2026.
- Consequence: all 96 booked units remain on time; no expiry; ending stock plus commitments falls from €355.20 to €259.20.

The unsafe explanation names the €30.00 temptation and the exact 12-unit booked-delivery loss. The control says plainly that no change is safer or lower exposure. Spreadsheet formula prefixes are neutralised, dates and units are explicit, and exported line totals plus delivery charge equal the selected cash total.

Evidence and all three drafts are under `artifacts/supplier-basket-showcase/phase-5/`.
