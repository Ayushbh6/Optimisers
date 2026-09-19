# Supplier Basket Review — Showcase Brief

**Status:** Technical release candidate complete on 18 September 2026. All seven implementation phases are frozen and reproducible; external buyer usability and pilot interest remain untested. Start with `docs/showcase/phase-7/SHOWCASE_RELEASE.md`.

## Main selling point

> **Turn messy distributor exports into a supplier-ready weekly purchase plan that shows where cash can be released without putting booked customer deliveries at risk.**

Short headline:

> **Buy less where it is safe. Protect every booked delivery.**

## Business question

> Before sending this week's purchase orders, can the buyer reduce unnecessary cash and stock while protecting booked customer deliveries?

## Marquee hypothesis

> Using only information available at ordering time, the product can reconcile messy operational records and identify lower-cash supplier-basket alternatives that preserve booked-order fulfilment exactly. When no safe alternative exists, it retains the buyer's original plan.

## Desired showcase outcome

The predeclared synthetic case study must demonstrate the complete buyer journey:

1. Import recognisably messy purchasing, stock, receipt, product, supplier and customer-order exports.
2. Preserve every original row and produce a visible issue register.
3. Separate safe automatic normalisation, buyer confirmation and hard blockers.
4. Reconcile the usable records into one traceable current stock, incoming and commitments position.
5. Reproduce the buyer's original weekly supplier basket.
6. Find at least one hand-verifiable MOQ or case-pack basket improvement.
7. Show the exact change in immediate cash and projected stock commitments while preserving every booked unit and promised delivery date in physical replay.
8. Reject an apparently cheaper alternative that creates a delivery or operational risk.
9. Return “keep the original order” in a genuine no-change control case.
10. Produce a supplier-ready draft showing quantities, cash required, expected arrivals, assumptions, delivery risks and leftover-stock consequences.

The exact products, quantities, dates and euro result must be calculated by hand and frozen before implementation. They must not be tuned after viewing software outcomes.

## Real-world data contract

The showcase will begin with raw, plausible exports rather than optimiser-ready tables. Its messiness must come from documented operational causes, not decorative random corruption. Examples may include:

- product and supplier aliases;
- cases versus individual units;
- duplicated or amended order lines;
- partial receipts and revised arrival dates;
- missing or contradictory dates;
- dated price and minimum-order changes;
- discontinued products and unknown references;
- stock snapshots that do not reconcile with movements.

The product must never silently invent a quantity, date, stock balance or supplier term. Ambiguity that changes the purchasing decision requires buyer confirmation or blocks the recommendation.

## Predeclared decision cases

The minimum showcase contains:

1. **Positive case:** a supplier minimum or case-pack distortion creates a safe, explainable lower-cash basket.
2. **Unsafe case:** a superficially cheaper basket is rejected because physical replay shows a booked-delivery or operational risk.
3. **No-change control:** the buyer's original basket is already appropriate and is retained.

Restricted spending and supplier disruption may be added only when they make the same buying decision clearer, not to create artificial feature breadth.

## Claim boundary

This will be a clearly labelled synthetic case study. It may demonstrate that the product correctly finds and explains a predeclared opportunity under those records. It must not claim realised client savings, general forecast accuracy, universal optimisation performance or willingness to pay.

## Next gate

Before generating data or building the application:

1. Specify the three cases in plain business facts.
2. Hand-calculate the buyer's basket, proposed basket and physical delivery consequences.
3. Freeze the raw-file schemas, deliberate data issues, correction rules and expected answers.
4. Review the complete case-study contract for realism, client relevance and honest claim boundaries.

Only after that review should dataset generation or product implementation begin.

The authoritative phase structure, test hierarchy, stop conditions and full Phase 1 protocol are in `docs/SUPPLIER_BASKET_IMPLEMENTATION_PLAN.md`.
