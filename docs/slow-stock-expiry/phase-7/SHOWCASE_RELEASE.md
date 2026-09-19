# Ledgerline Stock Watch — Showcase release

**Status:** Technical release candidate, 18 September 2026.

## What it demonstrates

> **Know what will run out, what may expire, and what to buy this week.**

The labelled synthetic showcase turns seven messy operational exports into a lot-level weekly action plan. It tells the buyer to order, keep, reduce/cancel or leave a plan alone, while protecting booked orders and customer shelf-life rules in four demand views.

## Frozen results

| Example | Buyer answer | Evidence |
|---|---|---|
| Balanced action | Order 2 Soup Cup cases; cancel 4 Oat Cracker cases | €82.00 → €58.00 purchase cash; booked units 36/60 → 60/60; higher-view expiry 72 → 24 units. |
| Unsafe shelf life | Keep 4 Fruit Bar cases | Existing lot has 8 days remaining against a 14-day customer requirement; lower incoming quantities fail booked or projected demand. |
| Healthy control | Keep 2 Tomato Jar cases | 36/36 booked units, higher/irregular demand protected, zero projected expiry. |

## Verification

- Independent Phase 1 arithmetic: PASS.
- Focused Stock Watch suite: 15 tests PASS.
- Complete repository suite: **203 tests and 9 subtests PASS**; two pre-existing `SyntaxWarning` messages remain in `src/simulation/report.py`.
- Real-browser positive, unsafe and healthy journeys: PASS; zero console errors/warnings.
- Desktop and 390px mobile screenshots: PASS.
- Read-only-compatible container build and health/result smoke: PASS. Image tested as `ledgerline-stock-watch:verification`; container returned the €58.00 balanced result.
- Release hashes: `artifacts/stock-watch-showcase/phase-7/release-manifest.json`.

## Run locally

```text
python3 -m src.stock_watch.webapp --port 8767
```

Open `http://127.0.0.1:8767/`.

Container:

```text
docker compose -f compose.stock-watch.yaml up --build
```

## Five-minute walkthrough

1. Choose **What needs changing this week?**
2. Confirm that the warehouse quantity means five cases / 60 units.
3. Read the two instructions: do not buy Oat Crackers; order two Soup Cup cases.
4. Compare purchase cash, projected expiry and booked orders before/after.
5. Download the order actions and expiry list.
6. Repeat the shelf-life example to show why apparent old stock cannot always replace an incoming order.
7. Repeat the healthy example to show that the product does not invent work.

## Honest boundary

This proves the frozen synthetic cases and application workflow. It does not prove realised savings, guaranteed waste prevention, general demand accuracy, a problem at a named company, or willingness to pay. A real pilot would require the buyer's lot, expiry, order, supplier and customer shelf-life records.
