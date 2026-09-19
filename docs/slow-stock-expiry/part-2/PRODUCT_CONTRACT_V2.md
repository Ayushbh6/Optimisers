# Stock Watch — Part 2 product contract, version 2

**Status:** Approved direction recorded, 18 September 2026. This replaces the proposed `PRODUCT_CONTRACT.md`, which remains as a superseded draft. No dataset, decision engine or application has started.

## What we are building

Before this week's order is sent, the buyer sees:

1. what will run out before the next possible delivery;
2. what may expire before it can be used or sold;
3. which lot should be used first;
4. what must be ordered now;
5. what should be bought less of, delayed or not bought at all.

Every answer must explain whether booked customer orders remain safe.

## Main selling point

> **Know what will run out, what may expire, and what to buy this week.**

Supporting line:

> **Buy what is needed. Do not buy stock you already have too much of. Use the oldest eligible stock first.**

## Business question

> **Before sending this week's orders, what do I need to buy now, what should I stop or reduce, and which stock needs using first so that customer orders are covered and stock does not expire unnecessarily?**

## Marquee hypothesis

> **Using records available on the review date, Stock Watch can combine stock by lot, expiry dates, booked customer orders, supplier delivery dates, open purchases and recent demand. It can then replay the next 28 days to show what will run out, what may expire, and whether the buyer should order, keep, reduce, delay or cancel each relevant purchase line. It keeps the current plan whenever a change would put a customer order at risk.**

## Scope of the first showcase

This is a bounded weekly decision tool, not a general demand-planning system.

- One illustrative food/FMCG distributor and one warehouse.
- Six to eight products, two suppliers and four to six customers.
- One 28-day consequence window.
- One fixed review date and known supplier order/receipt dates.
- Existing open purchase lines plus a small, bounded set of valid new-order or change options.
- Whole cases only; dated costs, supplier terms and change cut-offs are explicit.
- Booked customer orders are hard promises.
- Lower, nominal, higher and one irregular demand view are frozen before calculation.
- FEFO is applied only when the lot still meets the customer's remaining shelf-life requirement.

## What the product may recommend

For a product or purchase line, it may say:

| Buyer instruction | Meaning |
|---|---|
| **Order now** | Existing eligible stock will not cover the declared needs before the next possible receipt. |
| **Keep the order** | The open purchase is still needed. |
| **Buy less** | A valid whole-case reduction remains safe in every required view. |
| **Delay or cancel** | Supplier terms still permit it, and keeping it would leave unnecessary stock or expiry exposure. |
| **Use this lot first** | It is the oldest lot that still meets the customer’s shelf-life requirement. |
| **Buyer review needed** | A dated residual risk exists, but the system cannot honestly choose the commercial remedy. |
| **No action** | The current position is healthy. |

## Three predeclared showcase cases

### 1. Balanced action plan — buy one product, buy less of another

The buyer has two real decisions in the same weekly review:

- Product A will run out before its next possible supplier receipt unless a bounded order is placed now.
- Product B already has sufficient short-dated stock, but an open supplier line would add unnecessary stock that cannot be used in the 28-day window.

Expected result:

- order Product A in the valid whole-case quantity and show its receipt date;
- reduce, defer or cancel Product B only before its stated supplier cut-off;
- use the oldest eligible Product B lot first;
- protect every booked order and shelf-life rule across all frozen demand views;
- show cash added for Product A separately from cash avoided on Product B;
- show expiry and ending stock before and after.

This is the positive showcase case. It proves the full selling line without pretending every answer is “buy less.”

### 2. Unsafe-looking reduction — keep the order

Product C looks slow from recent sales and has old stock on hand. However, booked demand or a customer's minimum remaining shelf-life requirement means the old stock cannot safely replace the incoming line.

Expected result:

- show the tempting lower-cash action;
- identify the exact customer, quantity and date—or shelf-life rule—that fails;
- retain the current order;
- make clear why the oldest lot cannot be used for that delivery.

### 3. Healthy-position control — no action

The buyer's stock, lots and incoming orders are proportionate to the declared requirements. No product is about to run out and no lot has material avoidable expiry exposure.

Expected result:

- return **No action**;
- show the next review date and healthy stock runway;
- do not manufacture an ordering or expiry opportunity.

## Physical rules and decision order

Every candidate is replayed through the same lot-level warehouse sequence:

`opening lots → eligible receipts → FEFO allocation with shelf-life checks → booked dispatches → demand-view dispatches → expiry → closing stock and incoming commitments`

The product filters candidates in this order:

1. Enforce supplier order days, lead times, case sizes, supplier/product minimums, change cut-offs, budget, capacity and dated terms.
2. Preserve every booked customer dispatch and shelf-life requirement.
3. Do not reduce service in any frozen demand view.
4. Do not increase expiry in any frozen demand view.
5. Do not increase ending stock plus open incoming commitments.
6. Among survivors, prefer the lowest additional purchase cash.
7. Then prefer lower projected expiry and lower ending stock.
8. Break ties deterministically.

There is no selling-margin estimate, shortage penalty, markdown recommendation or weighted “business value” score.

## What the buyer must see

- product, lot and current quantity;
- expiry date or remaining shelf life, clearly labelled as `use by` or `best before`;
- next supplier delivery date and last date to change an open purchase;
- what runs out, and on what date, under each declared view;
- what expires or remains at risk, and why;
- the recommended order/change and exact case quantity;
- cash to commit and cash no longer committed, kept separate;
- booked deliveries protected and any rejected alternative;
- what remains a human commercial decision.

## Claim boundary

This is a clearly labelled synthetic case study. It may show that the frozen records produce the stated projected stock, expiry and purchase outcomes.

It must not claim realised savings, recovered revenue, guaranteed waste prevention, guaranteed sell-through, universal forecast accuracy, or a verified need at a named prospect. It must not say that `best before` stock is unsafe after its printed date.

## Approval guard

This contract is usable only if later hand calculations prove all of these:

- the “order now” instruction is necessary under the declared physical rules;
- the “buy less” instruction is safe in every frozen demand view;
- the unsafe case genuinely fails for a buyer-recognisable reason;
- the control case has no overlooked improvement;
- every action is permitted by the stated supplier terms;
- no result relies on future sales hidden from the buyer;
- a non-technical buyer can understand each instruction in five minutes.

## Next step

Part 3 defines the delivery phases and gates. The first implementation phase will create the hand-calculated business-case contract before any raw records or code are generated.
