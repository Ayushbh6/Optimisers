# Phase 1 — Hand-calculation review

**Result: PASS.**

The facts and expected answers were written before the Stock Watch engine. The independent script `artifacts/stock-watch-showcase/phase-1/verify_hand_truth.py` reproduces the three cash amounts, the positive expiry comparison, the unsafe shelf-life failure and the healthy stock balance without importing application code.

All quantities use whole units/cases. Supplier dates and cut-offs are visible. Booked demand is separate from projected demand. The positive result does not require a favourable demand view: two Soup cases and zero Oat cases remain the safe lowest-cash plan in all four views. The unsafe and healthy cases remain negative controls.

This proves the frozen synthetic arithmetic, not a prospect need or realised business result.
