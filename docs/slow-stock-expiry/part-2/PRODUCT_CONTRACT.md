# Slow-stock and expiry action planning — Part 2 product contract

**Status:** Superseded draft, 18 September 2026. It used vague positioning and a narrower purchase-reduction framing. The approved replacement is `PRODUCT_CONTRACT_V2.md`. No dataset, optimiser or application was started from this draft.

Read with:

- `docs/slow-stock-expiry/part-1/OPPORTUNITY_DIAGNOSIS.md`
- `docs/TARGET_CLIENTS.md`
- `docs/REPO_RULES.md`

## Product name

Working name: **Ledgerline Stock Watch**

This is a working product label, not a registered brand claim.

## Main selling point

> **Turn lot, expiry and purchasing records into a dated action plan—so buyers can stop avoidable stock arriving and act on short-dated inventory before time runs out.**

Short headline:

> **Act before slow stock becomes wasted cash.**

## Business question

> **Before confirming upcoming purchases, which incoming quantities can the buyer safely reduce or defer, and which existing lots need action before they become unusable or commercially stranded?**

“Commercially stranded” means stock that remains physically usable but is unlikely to satisfy the declared demand and customer shelf-life requirements before its decision deadline. It does not automatically mean legally unsafe or worthless.

## Marquee hypothesis

> **Using only information available at the review date, the product can reconcile lot-level stock, expiry dates, stock status, booked customer demand, minimum customer shelf life, incoming purchases and supplier change cut-offs; identify bounded purchase reductions or deferrals that remain safe under predeclared demand views; and expose any residual short-dated quantity with a clear action deadline. When no safe action exists, it retains the current plan.**

## Desired showcase outcome

The synthetic case study must demonstrate a complete buyer journey:

1. Import recognisably messy stock-lot, sales-order, purchase-order, receipt, product, customer and supplier-term exports.
2. Preserve every source row and distinguish automatic normalization, buyer confirmation and hard blockers.
3. Reconcile the records into one traceable position by product and lot: available, reserved, quarantined, incoming and committed.
4. Separate `use by`, `best before` and customer minimum-shelf-life rules.
5. Reproduce the buyer's current incoming-purchase plan and the warehouse's eligible FEFO allocation.
6. Show which quantities are projected to remain at risk under lower, nominal and higher demand views.
7. Find at least one hand-verifiable purchase reduction or deferral allowed by the supplier terms.
8. Replay the current and proposed plans through the same physical lot engine.
9. Preserve every booked customer delivery and shelf-life requirement in every required view.
10. Show exact changes in additional cash committed, incoming units, projected expiry, and ending stock plus commitments.
11. Reject an apparently attractive action that would create a delivery, shelf-life or supplier-term failure.
12. Return “no action” when the current stock and incoming plan are already appropriate.
13. Produce two buyer-ready outputs:
    - an incoming-purchase amendment draft; and
    - a dated residual-risk list for quantities that still need commercial review.

## The decision the product makes

For each reviewed product and open purchase line, the product may recommend exactly one of:

- **keep** the incoming quantity and date;
- **reduce** it by valid whole cases;
- **defer** it to a supplier-permitted date;
- **cancel** it before the contractual cut-off;
- **review residual stock** by a stated date, without prescribing a commercial outcome.

The product must also show when an apparently old lot is ineligible for a customer because too little shelf life would remain on delivery.

## Predeclared showcase cases

### Case 1 — Prevent avoidable overstock and expiry exposure

Business facts:

- usable lot stock already covers protected demand across all required demand views;
- one open incoming line is still legally and operationally changeable;
- keeping the line adds stock that cannot be consumed before the relevant expiry or decision horizon;
- a bounded whole-case reduction or permitted deferral removes that exposure.

Required result:

- exact lower additional cash commitment;
- unchanged booked deliveries and customer shelf-life compliance;
- no increase in expiry in any required view;
- lower ending stock plus incoming commitments;
- exact purchase line, quantity, deadline and supplier consequence shown.

### Case 2 — Reject a tempting but unsafe action

Business facts:

- recent sales make a purchase line appear unnecessary;
- booked demand, an eligible shelf-life constraint or a dated supply gap means the stock is still required;
- the cheaper action is otherwise plausible and respects whole-case rules.

Required result:

- exact apparent cash reduction;
- exact customer line, quantity, date or shelf-life rule that fails;
- retain the current incoming plan;
- explain why old on-hand stock cannot safely replace the incoming stock.

### Case 3 — Healthy-position control

Business facts:

- current stock, lot ages and incoming quantities are proportionate to the declared requirements;
- every bounded reduction, deferral or cancellation either violates terms or worsens a protected outcome;
- no residual lot crosses the declared action threshold.

Required result:

- retain the current plan;
- report no invented opportunity;
- show the healthy lot runway and next review date.

## Required demand views

The exact demand construction belongs to the later case contract, but the showcase must freeze it before reading outcomes and apply the same views to current and proposed plans:

- booked customer orders;
- lower recent-demand continuation;
- nominal recent-demand continuation;
- higher recent-demand continuation;
- at least one irregular historical order-pattern view.

Booked orders are a hard promise. Unbooked demand views are labelled projections, not known future sales. A positive action must not depend on selecting only the most favourable view.

## Decision hierarchy

Candidates are filtered, not assigned an invented business-value score.

1. Respect supplier change rights, whole cases, minimums, charges, budget, capacity and dated terms.
2. Protect every booked order and customer shelf-life requirement.
3. Do not reduce service in any required demand view.
4. Do not increase expired units or expiry cost in any required view.
5. Do not increase terminal stock plus incoming commitments.
6. Among survivors, minimise additional purchase cash.
7. Then minimise projected expiry units and cost.
8. Then minimise ending stock plus commitments.
9. Use stable deterministic tie-breaking.

No shortage penalty, selling margin, markdown assumption or weighted “business value” score is permitted.

## Buyer-facing explanation contract

Every recommendation must state:

- product and affected lot or purchase line;
- current quantity and recommended quantity/date;
- last date the buyer can act;
- additional cash before and after;
- booked units protected;
- customer shelf-life consequence;
- projected expiring units before and after, separated by demand view;
- remaining stock and incoming commitments;
- what is known, what is projected and what requires human commercial judgment.

## Claim boundary

The showcase may claim only that, under its labelled synthetic records and frozen assumptions, it:

- correctly reconciles lot-level stock and expiry information;
- reproduces the declared physical outcomes;
- identifies a supplier-permitted lower-commitment action in the positive case;
- rejects the unsafe action;
- retains the healthy control;
- quantifies projected exposure and its decision deadline.

It may not claim:

- realised client savings;
- guaranteed prevention of food waste;
- guaranteed sell-through or recovered revenue;
- that `best before` stock is unsafe after its date;
- universal demand accuracy or optimisation performance;
- that Lona, Matt Import or another prospect has the demonstrated problem;
- that a promotion, donation, return or disposal action is commercially or legally appropriate without the relevant evidence.

## Authoritative acceptance guard

Part 2 passes only if all statements below are true:

- [x] The selling point describes a buyer action, not a generic dashboard.
- [x] The hypothesis is testable using dated physical records.
- [x] Lot expiry and customer shelf-life are first-class constraints.
- [x] The positive case requires a competent, valid current plan—not an obviously foolish buyer action.
- [x] Unsafe and no-action results are mandatory.
- [x] Projected demand is visibly separated from booked demand.
- [x] Supplier change rights are explicit and dated.
- [x] The product does not optimise markdowns or invent recovered revenue.
- [x] The financial outcome is additional cash commitment, not realised savings.
- [x] The claim remains a labelled synthetic demonstration.

## Stop conditions

Stop and revise this contract before phase planning if:

- the user cannot understand the decision in a short buyer conversation;
- the product becomes only an ageing-stock report with no actionable decision;
- the positive outcome requires future customer orders;
- the case assumes a cancellation or deferral right absent from supplier terms;
- a customer shelf-life rule is ignored to create an improvement;
- the outcome depends on a tuned demand scenario;
- the proposed interface implies realised savings or guaranteed waste prevention.

## Part 2 decision

**Provisional PASS, pending user approval.** The contract is commercially distinct from Supplier Basket Review:

- Supplier Basket Review asks what to order this week.
- Stock Watch asks what existing and incoming stock will become a problem, what purchasing action remains possible, and when the buyer must act.

After approval, Part 3 should define the complete phase map, authoritative tests and stop/go guard for every phase. It must not generate data or code yet.
