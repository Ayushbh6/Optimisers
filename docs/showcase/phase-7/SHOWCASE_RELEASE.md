# Supplier Basket Review — v1 showcase release candidate

**Technical release: PASS — 18 September 2026. Commercial validation: not yet claimed.**

## What this honestly demonstrates

> Turn messy distributor exports into a supplier-ready weekly purchase plan that shows where cash can be released without putting booked customer deliveries at risk.

The frozen synthetic positive case finds a €96.00 lower-cash basket and protects all 96 booked units. Two equally polished controls show the other half of the promise: reject a cheaper unsafe edit and retain an already appropriate buyer order. These are case-study outcomes, not realised client savings or evidence of general optimiser performance.

## Launch

Local:

```sh
python3 -m src.supplier_basket.webapp --port 8765
```

Then open `http://127.0.0.1:8765`.

Container:

```sh
docker compose -f compose.showcase.yaml up --build
```

The container is dependency-free, read-only and health-checked. It was built and exercised on Docker 29.7.2; the positive API flow returned €524.00 and 96/96 booked units.

Verify frozen evidence:

```sh
python3 -m src.supplier_basket.cli verify
```

## Five-minute walkthrough

1. State the buyer question: “Before sending this week's purchase orders, can we release cash without putting booked deliveries at risk?”
2. Load **Safe minimum-order composition**. Point out the preserved raw-row count and unresolved UOM rather than jumping to the answer.
3. Confirm the recorded UOM. Show stock, incoming and 96 booked units before revealing the decision.
4. Compare €620.00 with €524.00. Explain the exact Honey Drops removal, Tomato Soup top-up, 22 September arrival and €259.20 ending exposure.
5. Load **Cheaper basket with delivery risk**. Show why €30.00 less cash is rejected: 12 booked Nougat Bars would be late.
6. Load **Keep the buyer order**. Resolve the signed supplier term and show the genuine no-change result.
7. Download one supplier draft and point to its input and decision hashes.

## Buyer-review questions

- Are these the records and exceptions your team actually handles before sending a weekly order?
- Which supplier minimums, case packs, delivery days, freshness promises and capacity constraints are missing?
- Is protecting booked deliveries the correct hard floor, or are there other commitments that must be equal?
- Would the side-by-side explanation be sufficient for a buyer to approve or reject a draft?
- Which one supplier and four weeks of real records would make a credible read-only pilot?

## Evidence boundary

The code and fixtures pass 188 tests plus 6 subtests on Python 3.12.13. A real browser exercises all three journeys, and a clean read-only container passes its health and positive-flow checks. Fresh evaluation seeds 91301–91305 were not opened. No external distributor has yet completed the five-minute review, so buyer usability and willingness to pilot remain the next commercial evidence—not another optimiser version.

The release manifest is `artifacts/supplier-basket-showcase/phase-7/release-manifest.json`.
