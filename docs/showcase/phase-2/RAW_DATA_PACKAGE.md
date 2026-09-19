# Supplier Basket Showcase — Phase 2 Raw Data Package

**Package version:** `supplier-basket-showcase-phase-2-v1`
**Frozen business contract:** `supplier-basket-showcase-phase-1-v1`
**Decision timestamp:** 18 September 2026 at 09:00 Europe/Vienna
**Nature of data:** Deliberately messy but operationally coherent synthetic exports.

## What this phase provides

Phase 2 turns the three Phase 1 paper cases into small source-system exports without changing their business truth.

`plausible raw exports → visible issue handling → normalized golden ledger → exact Phase 1 facts`

It does not contain importer code, optimiser output or UI files.

## Package layout

Each case under `artifacts/supplier-basket-showcase/phase-2/raw/` contains:

- `products.csv` — warehouse product master;
- `supplier_terms.csv` — purchasing terms valid at decision time;
- `stock_snapshot.csv` — lot-level usable stock;
- `customer_orders.csv` — booked lines and amendments;
- `purchase_orders.csv` — the buyer's draft basket and existing open orders;
- `receipts.csv` — linked goods receipts;
- `resolutions.csv` — explicit mappings, confirmations and authoritative replacements.

The package also contains:

- `golden/normalized-ledger.json` — the clean operational truth Phase 3 must reproduce;
- `issue-register.json` — every deliberate issue, business cause and required treatment;
- `row-accounting.csv` — one final state for every raw row;
- `verify_phase_2.py` — a standard-library audit independent of the future importer;
- `verification-report.json` — compact retained test evidence;
- `manifest.json` — source hashes and version identity.

## The three export sets

| Case | Raw rows | Buyer basket cash | Booked units | Purpose |
|---|---:|---:|---:|---|
| Positive MOQ composition | 24 | €620.00 | 96 | Alias, UOM confirmation and partial receipt while preserving the Phase 1 opportunity |
| Unsafe cheaper basket | 15 | €213.00 | 54 | Customer amendment that must resolve to the active 24-unit line |
| No-change control | 14 | €166.20 | 54 | Missing supplier minimum that blocks planning until a signed term replaces it |
| **Total** | **53** | **€999.20** | **204** |  |

These are independent snapshots, not three weeks of one evolving business.

## Realistic source systems

- `warehouse_erp` owns product references, stock lots and goods receipts.
- `sales_erp` owns booked customer lines and numbered amendments.
- `purchasing_erp` owns supplier terms and existing purchase orders.
- `buyer_workbook` contains the weekly draft baskets awaiting review.
- `supplier_portal_update` carries the revised ETA for an outstanding case.
- `signed_term_sheet` supplies the authoritative replacement for an incomplete ERP term.

The names are illustrative. No real company or software vendor is represented.

## Predeclared messiness

| Issue | Raw symptom | Required treatment | Final truth |
|---|---|---|---|
| `ISS-001` | `Tom Soup 12x400g` versus master reference `TS-400` | Safe alias mapping with original value retained | `PRD-001` |
| `ISS-002` | Draft quantity `5` has no UOM | Block until buyer confirms against `POS-PO-PDF-001` | Five cases = 60 tins |
| `ISS-003` | Customer line appears at amendment sequences 1 and 2 | Keep both; sequence 2 is active | 24 Nougat Bars |
| `ISS-004` | Two cases ordered, one received, remainder ETA revised | Link PO, receipt and update | 24 Tea boxes on hand + 24 incoming on 28 Sep |
| `ISS-005` | Current ERP supplier minimum is blank | Hard block until signed term supplied | €150 minimum from `CTL-TERM-PDF-001` |
| `ISS-006` | `ALDER`, `BEACON` and `Beacon Grocery` labels | Safe supplier-reference mapping | `SUP-A` or `SUP-B` |
| `ISS-007` | Receipt is visible in both stock and PO history | Linked reconciliation, not visual deduplication | Received case counted once |

## What the raw files deliberately do not reveal

The raw exports contain only the buyer basket and current operational records. They do not contain:

- the Phase 1 proposed basket;
- a “savings opportunity” flag;
- future customer orders;
- outcome labels inside the business rows;
- selling margins, penalty costs or a weighted score.

Developer folder names identify the fixture purpose, but no recommendation is encoded in the source records.

## Hard-blocking behaviour frozen for Phase 3

Two records demonstrate that correction cannot be silent:

1. Without `POS-RES-002`, the positive case cannot interpret quantity `5` as cases or units and must not plan.
2. Without `CTL-TERM-002` and `CTL-RES-005`, the control case cannot test the supplier minimum and must not plan.

After the explicit resolution records are present, all three golden cases have zero unresolved blockers.

## Claim boundary

The package is a coherent synthetic test fixture. It demonstrates how the later product must handle recognisable export problems. It is not evidence that these exact records came from Lona, Matt Import or another client, and it proves no realised saving.
