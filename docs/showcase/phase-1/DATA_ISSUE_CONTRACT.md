# Supplier Basket Showcase — Phase 1 Data Issue Contract

**Version:** `supplier-basket-showcase-phase-1-v1`
**Purpose:** Freeze Phase 2's operational messiness before any raw file is generated.

## Guard

Every raw row must survive with its source row ID. The system may normalize presentation, but it may not silently invent a product, quantity, unit, date, stock balance or supplier term.

`raw row → visible issue and provenance → automatic resolution, buyer confirmation or hard block`

## Frozen raw-file schemas

Phase 2 will create separate case folders using these CSV-compatible schemas.

| File | Required columns |
|---|---|
| `products.csv` | `source_row_id`, `source_system`, `product_ref`, `description`, `supplier_ref`, `base_uom`, `case_size`, `product_min_cases`, `unit_cost_eur`, `cost_effective_from`, `cost_effective_to` |
| `supplier_terms.csv` | `source_row_id`, `source_system`, `supplier_ref`, `supplier_name`, `order_weekday`, `lead_time_workdays`, `minimum_merchandise_eur`, `delivery_charge_eur`, `effective_from`, `effective_to` |
| `stock_snapshot.csv` | `source_row_id`, `source_system`, `snapshot_at`, `product_ref`, `lot_ref`, `quantity`, `uom`, `expiry_date` |
| `customer_orders.csv` | `source_row_id`, `source_system`, `order_ref`, `line_ref`, `amendment_sequence`, `status`, `customer_ref`, `product_ref`, `quantity`, `uom`, `booked_at`, `due_date` |
| `purchase_orders.csv` | `source_row_id`, `source_system`, `purchase_order_ref`, `line_ref`, `supplier_ref`, `product_ref`, `quantity`, `uom`, `ordered_at`, `expected_date`, `status` |
| `receipts.csv` | `source_row_id`, `source_system`, `receipt_ref`, `purchase_order_ref`, `line_ref`, `product_ref`, `quantity`, `uom`, `received_at`, `lot_ref`, `expiry_date` |
| `resolutions.csv` | `resolution_id`, `issue_id`, `resolution_type`, `chosen_value`, `evidence_ref`, `resolved_by`, `resolved_at` |

Blank optional fields are allowed only when they cannot change the decision. Decision-critical blanks follow the rules below.

## Predeclared issue register

| Issue ID | Case and source | Operational cause | Expected treatment | Frozen result |
|---|---|---|---|---|
| `ISS-001` | Positive, `products.csv` uses `Tom Soup 12x400g` | Purchasing and warehouse systems use different product labels | Safe automatic normalization with mapping provenance | Map uniquely to `PRD-001`; retain original text and mapping rule |
| `ISS-002` | Positive, `purchase_orders.csv` has quantity `5` with blank UOM for Tomato Soup | Supplier portal export omitted the display unit | Buyer confirmation required | Buyer confirms `5 cases`, supported by `POS-PO-PDF-001`; do not plan before confirmation |
| `ISS-003` | Unsafe, two rows exist for `UNS-CO-002` | Customer increased the line from 12 to 24 units after booking | Deterministic amendment resolution; retain both rows | Sequence 1 is superseded by sequence 2; active quantity is 24 units |
| `ISS-004` | Positive, Breakfast Tea PO and receipt | Supplier delivered one of two cases and revised the remainder | Deterministic reconciliation using linked receipt and dated supplier update | 24 boxes are in opening stock; 24 remain incoming for 28 September |
| `ISS-005` | Control, `supplier_terms.csv` has blank minimum on the current Beacon term | An incomplete ERP term export cannot establish basket validity | Hard blocker until authoritative replacement arrives | No recommendation until `CTL-TERM-PDF-001` establishes €150.00; original blank row remains visible |
| `ISS-006` | All cases use `Alder Fine Foods GmbH`, `ALDER`, or `SUP-A` | Supplier names differ across systems | Safe automatic normalization when tax/reference ID matches | Map to `SUP-A` with source labels retained |
| `ISS-007` | Positive stock snapshot and receipt both mention Breakfast Tea | A partial receipt can look like a duplicated open order if links are ignored | Linked reconciliation, never deduplication by appearance | Count 24 boxes on hand and 24 incoming—never 48 incoming or 48 on hand |

## Classification rules

### Safe automatic normalization

Allowed only when exactly one master record matches a predeclared alias or stable external reference. The output must show the source value, normalized value and mapping rule.

### Buyer confirmation

Used when the source contains a finite, understandable choice but the record itself is insufficient. The recommendation stays blocked until the choice and evidence reference are stored. Confirmation is not permission to type an arbitrary replacement.

### Hard blocker

Used when no valid purchasing decision can be established from the supplied records. A hard blocker clears only when an authoritative replacement record is supplied; the defective row is retained and marked superseded, never overwritten.

## Phase 2 row-accounting contract

Every row will end in exactly one state:

- `accepted_as_supplied`;
- `accepted_after_safe_normalization`;
- `superseded_by_amendment`;
- `accepted_after_buyer_confirmation`;
- `accepted_after_authoritative_replacement`; or
- `blocked_unresolved`.

Totals will be reconciled both before and after normalization. A raw row may contribute to operational truth once, not twice.

## Deliberately excluded fake messiness

Phase 2 will not add random typos, random nulls, impossible dates or unexplained stock adjustments merely to make the files look difficult. Every defect above represents a recognisable operational cause and a testable product response.
