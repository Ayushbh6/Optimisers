# Phase 4 — Exact inventory decision review

**Result: PASS.**

The search is capped at 25 plans. Every feasible whole-case plan is replayed through the same lot receipts, customer shelf-life eligibility, FEFO dispatch, four demand views and expiry process. The selected plan exactly matches a fresh replay.

- Balanced: two Soup cases, zero Oat cases; €82.00 → €58.00; 60/60 booked units; higher-view expiry 72 → 24.
- Unsafe: retain four Fruit cases; reductions fail booked shelf life or projected service.
- Healthy: retain two Tomato cases; no projected expiry.

No score, penalty, margin or tuned parameter selects the answer.
