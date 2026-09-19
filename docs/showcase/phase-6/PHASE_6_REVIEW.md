# Phase 6 — Client application review

**Technical gate: PASS — 18 September 2026. Human usability validation remains external.**

The local application completes the full records-to-supplier-draft journey on `http://127.0.0.1:8765`. Port 3000 is never used.

Following direct usability feedback, the original five-stage audit presentation was removed from the buyer-facing screen. The current interface has three genuinely clickable, plain-English example choices, one **Review this order** action, at most one required confirmation, and one recommendation. Row counts, hashes and automatic reconciliation checks are available only under optional technical details.

Verified in a real browser:

- positive case stops for the missing UOM, accepts the recorded confirmation, reconciles and exports the €524.00 basket;
- unsafe case retains the €213.00 buyer basket and exposes the €30.00 / 12-unit trade-off;
- no-change case stops on the missing supplier minimum, accepts the signed term, then retains €166.20;
- reset deletes the active in-memory session;
- 390 × 844 responsive layout works;
- final browser run has zero console errors;
- semantic landmarks, focus-visible styling and reduced-motion behaviour are present.

The application uses strict automatic mapping for the frozen seven export schemas. Schema drift is rejected visibly rather than guessed through an interactive mapper. Sessions are memory-only, isolated, capped at 32 and removable through the reset control.

Screenshots and the browser evidence record are under `artifacts/supplier-basket-showcase/phase-6/`. Browser automation establishes functional operability; it does not substitute for watching a new buyer use the product.
