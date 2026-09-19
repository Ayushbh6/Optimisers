# Phase 3 — Import and reconciliation review

**Technical gate: PASS — 18 September 2026.**

The importer accepts exactly the seven frozen CSV schemas, preserves original text and source-row IDs, and uses the independently specified Phase 2 issue register. It does not silently fill decision-critical facts. A missing draft UOM and a missing supplier minimum both stop planning until their recorded evidence is explicitly accepted.

| Case | Raw rows | Initial state | Reconciled output hash | Golden match |
|---|---:|---|---|---|
| Safe minimum-order composition | 24 | Blocked on UOM confirmation | `9b509b85b29f431a8b55ae53d5e50738c8681aeafe44888dedeb2d04d2315358` | Exact |
| Cheaper basket with delivery risk | 15 | Ready | `4b46662be3848baecf0d09bdce9e1e0b0cebe0288a2024b9ccd1194657775333` | Exact |
| Keep the buyer order | 14 | Blocked on authoritative term | `d2a0caa34b798196b66edeedd85ccd558d6de1c4213f58f3ada1769279ac0812` | Exact |

All 53 raw rows remain identifiable. Aliases, the customer amendment, the partial receipt and its revised ETA reconcile without double-counting. Re-import and reconciliation are deterministic. A new upload creates a new input hash and isolated session, so an earlier decision is not reused.

Evidence: `artifacts/supplier-basket-showcase/phase-3/verification-report.json` and `tests/test_supplier_basket_showcase.py`.

This passes the Phase 3 technical gate. It proves the frozen synthetic imports, not arbitrary client schemas or data quality in general.
