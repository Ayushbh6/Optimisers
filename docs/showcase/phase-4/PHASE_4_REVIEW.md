# Phase 4 — Exact purchasing decision review

**Technical gate: PASS — 18 September 2026.**

The engine starts with the buyer basket, creates a deterministic whole-case neighbourhood, enforces supplier minimum, product minimum, weekly allowance, receipt capacity, order date, dated terms and arrival date, then judges every feasible alternative through the same 28-day FEFO warehouse replay.

| Case | Generated / physically replayed | Buyer cash | Selected cash | Booked on time | Ending stock + commitments | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Safe minimum-order composition | 9 / 8 | €620.00 | €524.00 | 96 / 96 | €259.20 | Revise |
| Cheaper basket with delivery risk | 10 / 9 | €213.00 | €213.00 | 54 / 54 | €0.00 | Retain |
| Keep the buyer order | 12 / 9 | €166.20 | €166.20 | 54 / 54 | €0.00 | Retain |

The positive basket removes one Honey Drops case and increases Tomato Soup from five to eight cases. It reproduces the hand result exactly: €96.00 less immediate cash, the same 96 on-time booked units, no expiry and €96.00 less ending stock plus commitments. The challenged €183.00 unsafe basket is rejected because 12 Nougat Bar units due 24 September would be late. The control exhausts the frozen 12 alternatives and keeps the buyer order.

Every selected prediction equals a fresh independent call to the physical replay byte-for-byte. Search is capped at 12 alternatives and two changed lines. The retained run completed each search in under 3 ms on Darwin arm64; that is a named development measurement, not a production SLA.

No selling margin, shortage penalty, weighted score, future order or evaluation seed is used. Evidence: `artifacts/supplier-basket-showcase/phase-4/decision-results.json`.
