# Slow-stock and expiry action planning — Part 1 opportunity diagnosis

**Status:** Initial mechanism review complete, 18 September 2026. This is not yet the frozen showcase brief, dataset contract or implementation plan.

## Purpose

Decide whether there is a commercially useful, honestly demonstrable inventory decision before writing a USP, generating example data or building software.

The proposed user is a food/FMCG distributor buyer or inventory controller. Lona and Matt Import are relevant prospects by sector, but their actual records, processes and problems have not been inspected.

## Candidate business question

> Which stock is likely to become excess or expire, and what can the buyer still do before committing more cash?

This wording is provisional. Part 2 must freeze the final selling point, marquee hypothesis and desired outcome.

## Operational facts established

1. Expiry must be tracked by **lot**, not only by product total. Two cases of the same product can require different actions because their expiry dates differ.
2. FEFO means allocating the earliest-expiring eligible lot first. It is an established warehouse rule, not a novel optimiser feature.
3. FEFO is constrained by the customer's required remaining shelf life. The oldest lot cannot be sent merely because it expires first if it would arrive too short-dated.
4. `Use by` and `best before` are not interchangeable. EU rules treat `use by` as a safety date for highly perishable food; `best before` concerns minimum durability/quality.
5. A recommendation to reduce, defer or cancel incoming supply is legitimate only when the purchase line is still changeable under visible supplier terms.
6. A system may project an expiry exposure. It cannot honestly promise a markdown, promotion or recovered revenue without customer response and commercial evidence.

Primary references:

- EU Regulation 1169/2011, Articles 24–25 and Annex X: <https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=celex:32011R1169>
- Oracle Warehouse Management allocation methods, including FEFO: <https://docs.oracle.com/en/cloud/saas/warehouse-management/26a/owmol/optional-step-additional-configuration-parameters.html>
- Oracle NetSuite FEFO lot assignment and customer shelf-life requirements: <https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_161009052865.html>

These sources establish operational legitimacy. They do not establish a problem or savings amount for a specific prospect.

## Initial mechanism tests

The figures below are small diagnostic examples, not proposed showcase cases. They test whether each mechanism can produce a traceable decision.

### Test A — Stop avoidable incoming supply

Decision date: 18 September. One product has 120 usable units on hand. Protected demand plus the declared high-demand view requires 72 units before the relevant lots expire. A changeable incoming order contains 96 units at €2.00 each.

| Position | Keep incoming | Remove incoming |
|---|---:|---:|
| Available units | 216 | 120 |
| Required units | 72 | 72 |
| Units remaining | 144 | 48 |
| Additional cash committed | €192 | €0 |

Result: **viable mechanism**. Removing the incoming 96 units avoids €192 of additional commitment while leaving the full 72-unit requirement covered. This is valid only if cancellation/reduction is contractually allowed and exact physical replay confirms every required dispatch.

### Test B — FEFO allocation with customer shelf-life protection

There are 60 units expiring in 30 days and 60 units expiring in 120 days. A customer order for 36 units arrives in five days and requires at least 20 days of remaining shelf life.

- Old lot at customer receipt: 25 days remaining — eligible.
- New lot at customer receipt: 115 days remaining — eligible.
- Correct allocation: 36 units from the old lot.

Result: **necessary operational rule, but not a standalone USP**. FEFO can reduce avoidable ageing, but ordinary FEFO alone is already standard warehouse practice. The showcase should demonstrate its interaction with purchasing, commitments and shelf-life rules.

### Test C — Commercial action for unavoidable residual stock

Suppose 48 short-dated units remain after all protected demand and every removable incoming order has been addressed.

Result: **useful escalation, not an optimisation claim**. The product may show the exact quantity, cost exposure and last useful action date. It must not invent a discount, selling price, recovered revenue or probability of sale. The buyer decides whether to promote, return, donate, transfer or dispose, subject to their real commercial and regulatory rules.

### Test D — False-alarm control

One product appears slow from recent sales, but 80 units are already committed to dated customer orders. Only 84 eligible units will be available before those due dates.

Result: **required negative case**. The system must protect the stock and reject a purchase cancellation or commercial clearance recommendation that would make the commitments unsafe.

## Mechanism verdict

The strongest product mechanism is:

> Reconcile lot-level stock, dated customer requirements, eligible incoming supply and changeable purchase commitments; replay the position under predeclared demand views; remove only incoming supply that is unnecessary in every required view; then expose any residual expiry risk as a dated buyer action.

This creates a defensible chain:

`messy lot and order records → traceable stock position → exact physical replay → safe supply action → residual risk for buyer review`

## What the product may decide

- retain an incoming purchase line;
- reduce it by valid whole cases;
- cancel it when the supplier terms permit;
- defer it to a permitted later date;
- choose an eligible FEFO lot for a protected customer dispatch;
- escalate a specific residual quantity for buyer/commercial action;
- return “no action” when the position is healthy or action would create risk.

## What the product must not decide without additional evidence

- an optimal markdown or promotion;
- expected recovered revenue;
- a supplier return right that is absent from the terms;
- disposal or donation legality;
- future demand selected to manufacture a favourable result;
- that all `best before` stock becomes waste on the printed date;
- that projected avoided purchasing is realised savings.

## Information required for a defensible case study

- product and lot identifiers;
- quantity, base unit and case conversion;
- receipt date and `use by` or `best before` date;
- stock status such as available, reserved, quarantined or damaged;
- customer commitments, due dates and minimum remaining shelf-life rules;
- open purchase lines, expected arrivals and change/cancellation cut-offs;
- dated purchase cost, delivery charge and supplier/product minimums;
- recent demand observations available at the decision time;
- predeclared lower, nominal and higher demand views;
- physical receipt, allocation, dispatch and expiry rules.

## Part 1 gate assessment

| Test | Result | Reason |
|---|---|---|
| Clear buyer decision | PASS | Act before more cash is committed or the intervention window closes. |
| Traceable physical consequence | PASS | Units, lots, dates, commitments and cash can be replayed exactly. |
| Negative outcome supported | PASS | False-alarm and healthy-stock controls are natural. |
| Established operational practice | PASS | Lot expiry, FEFO and minimum customer shelf life are documented system practices. |
| Honest financial measure | PASS WITH LIMIT | Avoided additional commitment is measurable; realised savings and recovered revenue are not. |
| Prospect-specific need proven | NOT YET | No Lona or Matt Import operating records or buyer interview have been reviewed. |
| Final USP and hypothesis frozen | NOT YET | This belongs to Part 2 after user review. |

## Stop conditions for the next part

Do not proceed to synthetic cases if the proposed result requires any of the following:

- treating product-level stock as if lot dates do not matter;
- ignoring customer minimum shelf-life requirements;
- cancelling a purchase after its change cut-off;
- using only a favourable demand view;
- treating ordinary FEFO as proprietary optimisation;
- prescribing a promotion or recovered revenue without evidence;
- describing projected expiry avoidance as realised client savings.

## Recommended Part 2

Freeze the product contract:

1. final main selling point;
2. exact business question;
3. marquee hypothesis;
4. desired showcase outcome;
5. positive, unsafe and no-action case archetypes;
6. claim boundary and acceptance guard.

Only after that contract is approved should the full phase plan be written.
