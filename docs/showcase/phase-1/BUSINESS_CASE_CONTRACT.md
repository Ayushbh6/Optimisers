# Supplier Basket Showcase — Phase 1 Business Case Contract

**Version:** `supplier-basket-showcase-phase-1-v1`
**Decision time:** 18 September 2026 at 09:00 Europe/Vienna
**Nature of evidence:** Predeclared, synthetic and hand-calculated. No client saving is claimed.

Read the shared rules in `OPERATIONAL_RULES.md`. Each case below starts from its own declared records; cases do not evolve into one another.

## The commercial question

> Before sending this week's purchase orders, can the buyer reduce unnecessary cash and stock while protecting booked customer deliveries?

## Case 1 — Safe supplier-minimum composition change

### Business facts

The buyer must order from Alder Fine Foods, whose merchandise minimum is €500. The buyer's genuinely required Tomato Soup and Oat Crackers total only €360. Their normal manual top-up is one case of Honey Drops, bringing merchandise to €600.

This is a valid and plausible basket: Honey Drops is a normal stocked item, not a fake or invalid line. The opportunity is that a smaller-value top-up can instead be placed into Tomato Soup, which is already needed.

Opening and existing incoming position:

| Record | Product | Quantity | Availability | Expiry | Cost value |
|---|---|---:|---|---|---:|
| `POS-STK-001` | Tomato Soup | 12 tins | Opening | 31 Dec 2026 | €48.00 |
| `POS-STK-008` | Breakfast Tea | 24 boxes | Opening from partial receipt | 28 Feb 2027 | €57.60 |
| `POS-INC-008` | Breakfast Tea | 24 boxes | Revised arrival 28 Sep | 28 Feb 2027 | €57.60 |

The Breakfast Tea order was for 48 boxes. Twenty-four arrived on 15 September; the remaining 24 have a supplier-confirmed revised arrival of 28 September. It is identical under both compared baskets.

Booked customer lines:

| Line | Due date | Product | Units |
|---|---|---|---:|
| `POS-CO-001` | 21 Sep | Tomato Soup | 12 |
| `POS-CO-002` | 23 Sep | Tomato Soup | 36 |
| `POS-CO-003` | 23 Sep | Oat Crackers | 12 |
| `POS-CO-004` | 25 Sep | Tomato Soup | 24 |
| `POS-CO-005` | 25 Sep | Oat Crackers | 12 |

### Buyer basket and proposed basket

Both arrive on 22 September and pass the €800 allowance and 250-unit receipt capacity.

| Product | Buyer cases | Buyer units | Buyer value | Proposed cases | Proposed units | Proposed value |
|---|---:|---:|---:|---:|---:|---:|
| Tomato Soup | 5 | 60 | €240.00 | 8 | 96 | €384.00 |
| Oat Crackers | 2 | 24 | €120.00 | 2 | 24 | €120.00 |
| Honey Drops | 1 | 24 | €240.00 | 0 | 0 | €0.00 |
| **Merchandise** |  |  | **€600.00** |  |  | **€504.00** |
| Delivery |  |  | €20.00 |  |  | €20.00 |
| **Immediate cash** |  |  | **€620.00** |  |  | **€524.00** |

The proposed basket removes one Honey Drops line and uses the smallest three-case Tomato Soup increase that restores the €500 supplier minimum.

### Frozen verdict

**ACCEPT THE PROPOSED BASKET.** It requires exactly **€96.00 less immediate cash**. Both baskets ship all 96 booked units across all five lines on their original dates. Neither expires stock. Ending stock plus incoming commitments falls from **€355.20 to €259.20**, also €96.00 lower.

The buyer is not told that Honey Drops will never sell. The claim is narrower: across the declared 28-day booked-order view, the alternative puts less purchase-cost value into leftover stock without weakening any booked delivery.

## Case 2 — Cheaper basket rejected by physical replay

### Business facts

The buyer's Beacon Grocery Supply basket covers four booked lines. A superficially cheaper edit removes one Nougat Bars case and adds one Pasta case. It still passes the supplier minimum, budget and capacity rules.

Opening stock:

| Record | Product | Quantity | Expiry | Cost value |
|---|---|---:|---|---:|
| `UNS-STK-004` | Nougat Bars | 12 packs | 31 Dec 2026 | €60.00 |

Booked customer lines:

| Line | Due date | Product | Units |
|---|---|---|---:|
| `UNS-CO-001` | 21 Sep | Nougat Bars | 12 |
| `UNS-CO-002` | 24 Sep | Nougat Bars | 24 |
| `UNS-CO-003` | 25 Sep | Olive Oil | 6 |
| `UNS-CO-004` | 26 Sep | Pasta | 12 |

### Buyer basket and challenged basket

Both arrive on 23 September.

| Product | Buyer cases | Buyer value | Challenged cases | Challenged value |
|---|---:|---:|---:|---:|
| Nougat Bars | 2 | €120.00 | 1 | €60.00 |
| Olive Oil | 1 | €48.00 | 1 | €48.00 |
| Pasta | 1 | €30.00 | 2 | €60.00 |
| **Merchandise** |  | **€198.00** |  | **€168.00** |
| Delivery |  | €15.00 |  | €15.00 |
| **Immediate cash** |  | **€213.00** |  | **€183.00** |

### Frozen verdict

**REJECT THE CHALLENGED BASKET.** The apparent cash reduction is **€30.00**, but the opening 12 Nougat Bars ship on 21 September. The challenged receipt then supplies only 12 of the 24 Nougat Bars due on 24 September. Exactly **12 booked units are late**, and that customer line is incomplete.

The extra Pasta leaves €30.00 of stock while the missed Nougat commitment is worth €60.00 at purchase cost. Ending stock plus undelivered commitments is therefore €90.00 instead of €0.00. The physical consequence—not a penalty score—rejects the edit.

## Case 3 — Genuine no-change control

### Business facts

The buyer has no usable opening stock for the three products below. The Beacon basket is only €1.20 above its €150 merchandise minimum, and every ordered unit has a booked use.

Booked customer lines:

| Line | Due date | Product | Units |
|---|---|---|---:|
| `CTL-CO-001` | 24 Sep | Olive Oil | 6 |
| `CTL-CO-002` | 25 Sep | Pasta | 12 |
| `CTL-CO-003` | 28 Sep | Pasta | 12 |
| `CTL-CO-004` | 29 Sep | Chickpeas | 24 |

Buyer basket, arriving 23 September:

| Product | Cases | Units | Value |
|---|---:|---:|---:|
| Olive Oil | 1 | 6 | €48.00 |
| Pasta | 2 | 24 | €60.00 |
| Chickpeas | 2 | 24 | €43.20 |
| **Merchandise** |  |  | **€151.20** |
| Delivery |  |  | €15.00 |
| **Immediate cash** |  |  | **€166.20** |

### Frozen neighbourhood result

- Each direct one-case reduction falls below the €150 supplier minimum.
- Each one-line increase protects deliveries but raises cash and leaves stock.
- Each permitted minimum repair shifts cases away from a product with a booked requirement. The repaired basket either costs more than the buyer basket or misses that product's booked line.
- Product substitution is forbidden.

### Frozen verdict

**RETAIN THE BUYER BASKET.** It ships all 54 booked units across all four lines on time, expires nothing and ends with no stock or undelivered commitment. There is no safe lower-exposure or lower-cash survivor inside the declared bounded neighbourhood.

## Why the three cases support the USP honestly

| Required behaviour | Evidence in this contract |
|---|---|
| Release avoidable cash safely | Case 1 changes supplier-minimum composition and protects every booked unit |
| Reject a tempting but unsafe edit | Case 2 shows the exact customer line, date and 12-unit failure |
| Avoid inventing an opportunity | Case 3 returns “retain” after every bounded edit fails |
| Remain understandable | Every result comes from cases, units, dated costs, fees and physical stock movements |

The contract demonstrates intended software behaviour under stated synthetic conditions only. It does not establish realised savings, universal optimisation performance or client willingness to pay.
