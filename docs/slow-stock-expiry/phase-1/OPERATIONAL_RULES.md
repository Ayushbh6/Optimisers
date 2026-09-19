# Phase 1 — Operational rules

- One warehouse; review date 5 October 2026; 28 calendar days.
- Daily order: lots already past their printed date become unavailable, receipts enter, booked orders dispatch, projected demand dispatches, then stock closes.
- FEFO uses the earliest-expiring eligible lot.
- A lot is eligible only when its remaining shelf life on dispatch meets the customer's rule.
- Only `AVAILABLE` stock may dispatch.
- Supplier orders use whole cases. Orders/change decisions occur Monday, arrive after four days, stay within €300 and 200 receipt units.
- Purchase cash equals merchandise plus the €10 delivery charge when at least one line remains.
- The four demand views are lower, nominal, higher and irregular. They are applied unchanged to every plan.
- Candidates cannot lose booked delivery, projected service, expiry or ending-stock performance against the current plan.
- Selection then uses lowest purchase cash, lower expiry, lower ending stock and a stable tie-break.
- No margin, markdown, shortage penalty or weighted score is used.
