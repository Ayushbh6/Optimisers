# Supplier Basket Showcase — Phase 1 Operational Rules

**Contract version:** `supplier-basket-showcase-phase-1-v1`
**Frozen decision timestamp:** 18 September 2026 at 09:00 Europe/Vienna
**Physical consequence window:** 18 September–15 October 2026 inclusive (28 calendar days)
**Status:** Frozen illustrative assumptions for a synthetic case study. They are not client observations.

## What the decision is

The buyer has prepared this week's purchase orders. The product may change whole-case quantities inside one supplier basket only when exact physical replay shows that the changed basket protects every booked delivery.

`records known by 09:00 → valid whole-case baskets → exact receipts and dispatches → accept, reject or retain`

Unknown future orders, selling prices, margins and shortage penalties are outside the decision.

## Shared operating sequence

Each case is an independent snapshot of the same fictional business, **Northstar Pantry Distribution GmbH**, operating one warehouse.

On every day:

1. At 00:01, expired stock is quarantined and cannot ship.
2. At 08:00, receipts due that day enter their declared lot.
3. At 12:00, booked customer lines due that day dispatch using first-expiry-first-out stock.
4. A line may ship partially. Units not shipped by its due date are late immediately; the lateness allowance is zero days.
5. At 18:00, closing usable stock and still-open incoming quantities are measured.

An order placed on Friday counts Monday as working day one. Supplier closures and public holidays are absent from this frozen example.

## Delivery promise and freshness

- The hard promise is every already-booked unit on its stated delivery date.
- A customer line is complete only when all its units ship by that date.
- A lot is eligible only when at least **60 calendar days** remain before its expiry date on dispatch day.
- No substitution is allowed between products.
- Unshipped units remain visible as undelivered commitments through the end of the 28-day window.

## Money and stock measures

- Currency: EUR.
- Product costs and delivery charges exclude VAT. VAT is omitted because it is recoverable and does not distinguish the baskets.
- Immediate cash required = ordered units × dated unit cost + supplier delivery charge.
- Supplier minimums apply to merchandise value before the delivery charge.
- The weekly purchasing allowance is **€800 including delivery charges** for each independent case.
- Stock and incoming commitments are valued at the same dated unit purchase cost.
- The daily exposure measure is closing usable stock value + unreceived committed stock value + past-due undelivered booked-unit value. Future booked lines are protected by replay but are not counted as stock exposure before their due date.
- Average exposure is the sum of the 28 daily exposure values divided by 28.
- Expiry is measured in units and purchase-cost euros.

## Capacity

- The warehouse may receive at most **250 base units per day**.
- Every declared basket is checked against the capacity before physical replay.
- There is no opening warehouse-wide capacity backlog in these cases.

## Supplier terms

The terms below are effective from 1 September through 31 December 2026.

| Supplier | Order day | Lead time | Expected arrival | Minimum merchandise | Delivery charge |
|---|---|---:|---|---:|---:|
| Alder Fine Foods (`SUP-A`) | Friday | 2 working days | Tuesday 22 September | €500.00 | €20.00 |
| Beacon Grocery Supply (`SUP-B`) | Friday | 3 working days | Wednesday 23 September | €150.00 | €15.00 |

There is no free-delivery threshold. Every accepted basket pays the stated charge.

## Product terms

Every order quantity must be a positive whole number of cases. The minimum for every ordered product is one case.

| Product | Supplier | Base unit | Case size | Unit cost | Case value |
|---|---|---|---:|---:|---:|
| Tomato Soup (`PRD-001`) | SUP-A | tin | 12 | €4.00 | €48.00 |
| Oat Crackers (`PRD-002`) | SUP-A | pack | 12 | €5.00 | €60.00 |
| Honey Drops (`PRD-003`) | SUP-A | jar | 24 | €10.00 | €240.00 |
| Nougat Bars (`PRD-004`) | SUP-B | pack | 12 | €5.00 | €60.00 |
| Olive Oil (`PRD-005`) | SUP-B | bottle | 6 | €8.00 | €48.00 |
| Pasta (`PRD-006`) | SUP-B | pack | 12 | €2.50 | €30.00 |
| Chickpeas (`PRD-007`) | SUP-B | tin | 12 | €1.80 | €21.60 |
| Breakfast Tea (`PRD-008`) | SUP-B | box | 24 | €2.40 | €57.60 |

All new showcase receipts expire on 31 January 2027, except the existing Breakfast Tea purchase order, which expires on 28 February 2027. The opening lots expire on 31 December 2026. All are eligible under the 60-day rule throughout the window.

## Bounded basket neighbourhood

The later decision engine must reproduce this frozen boundary; it may not widen it after seeing results.

1. Start from the buyer's basket.
2. Generate each complete line removal.
3. Generate a one-case reduction and a one-case increase for every ordered line where the quantity remains valid.
4. If a removal or reduction falls below the supplier minimum, repair it by increasing **one other product already needed in that case** by the smallest whole-case quantity that restores the minimum.
5. At most two product lines may differ from the buyer basket.
6. Do not add a new supplier or change dates, prices, case sizes or delivery charges.
7. Reject rule-invalid baskets before replay.
8. Replay every rule-valid basket exactly. Protect booked units first; among equally safe baskets choose the lower average exposure, then lower expiry, then lower delivery charge, then the lexicographically smallest ordered `(product_id, cases)` list.
9. Immediate cash is reported, not used as an arbitrary weighted score. In the positive case the lowest-exposure safe survivor also requires the least immediate cash.

The neighbourhood is deliberately small and explainable. It is a showcase contract, not a universal purchasing policy.

## Accounting identity

For each product and each day:

`opening usable units + receipts - dispatched units - expired units = closing usable units`

There are no stock adjustments in Phase 1. Any non-zero unexplained difference fails the phase.
