# Initial stock-ordering opportunity screen — 15 September 2026

## Decision

Continue toward **short-term forecast-informed replenishment**, with booked-order risk and explanations as the visible user workflow. Do not make rearranging current stock or purchasing only against orders already received the primary value claim. This screen identifies a direction; it does not establish a winning replenishment policy or client savings.

The eight-month dataset remains suitable for this bounded question. Its own timing creates a real need to anticipate near-term orders; extending it to years is unnecessary for that question. A later seasonal-planning demo remains separate.

## What the data establishes

The retained synthetic history has 30 products, 864 customer order lines and 7,594 requested units. Customers normally request delivery 1–3 working days after booking. Suppliers accept orders on a particular weekday and normally take 2–6 working days in this retained scenario.

For **90.57% of requested units**, a purchase first placed after the customer booking, on the next allowed supplier ordering day, could not arrive by the original customer due date—even with normal supplier performance. For **64.77%**, it could not arrive even within the customer's allowed late-delivery window. This is a timing bound within the constructed business, not evidence about Lona or Matt Import.

Cause and effect: **short customer notice + slower supplier replenishment → stock must often be ordered before the individual customer order arrives**. Forecasting should support that ordering decision; it need not be the demo's headline.

## Fixed exploratory scope

The [protocol](../artifacts/distributor-demo/exploration/PROTOCOL.md) was recorded before results. One development seed (1101), three families (ordinary, restricted spending, supplier disruption), and 12 Monday–Thursday dates from 16 June to 3 July were included. All products and all still-open customer order lines were retained in each snapshot. These are **36 overlapping decision snapshots**, not independent customers, additive evaluation periods or a held-out study.

Two supply assumptions were assessed for every snapshot:

- Projected case: outstanding supplier quantities use the latest released ETA; new orders use normal lead time. Receipt freshness is assumed to be at least 60 days on arrival. PO-level update granularity is a simplification.
- Stress case: pending stock is unavailable and new orders arrive two working days later. This is a deliberately adverse bound, not a probability forecast.

Three probes were compared: due-date/earliest-expiry allocation without new purchases; exact allocation without new purchases; and joint case ordering plus allocation to current bookings. Both exact probes maximise booked units served within the allowed customer window, then minimise additional spending. They respect case sizes, product and supplier minimums, order calendars, the remaining weekly budget, delivery charges and whole-line customer requirements.

Storage uses a conservative peak bound before any dispatch. The selected snapshots did not exercise capacity overflow or overdue unscheduled incoming stock; the broader dataset tests cover those behaviours. Future unknown customer demand is not modelled. The screen never reads evaluator data for a decision.

## Results

| Development family | Snapshots | Better allocation helped (projected supply) | New buying added booked coverage (projected supply) | New buying added coverage under stress |
|---|---:|---:|---:|---:|
| Ordinary | 12 | 1 | 4 | 1 |
| Restricted spending | 12 | 1 | 5 | 1 |
| Supplier disruption | 12 | 1 | 3 | 4 |
| **Total** | **36** | **3** | **12** | **6** |

Most snapshots did not justify new purchases for the booked orders alone: **24/36** under projected supply and **30/36** under stress. The two assumption cases have different available stock, so their improvements cannot be compared as realised performance or summed.

One revealing example, selected after inspecting the complete screen: in the supplier-disruption snapshot on 30 June, allocation alone could project coverage of 167 of 209 booked units. Maximising booked coverage bought **72 units for €596.64 including delivery**, raising coverage by only **eight units**, to 175. The remaining 64 purchased units have no demonstrated value in this bookings-only calculation. They are not necessarily waste—future demand is absent—but the screen cannot justify them economically.

That example shows why "maximise fulfilled units, then minimise spend" is insufficient as a commercial objective. A buyer needs the expenditure and leftover-stock consequence explained, with a meaningful service-versus-stock trade-off. Lower purchase spending alone would not be profit either.

## What to explore in the full plan

The proposed buyer-facing promise is: **"Know what to order now, what can wait, and which customer commitments remain at risk."**

1. Estimate short-term demand from history available at the decision date, and combine it with booked orders without counting them twice.
2. Compare a competent stock-cover rule with joint supplier/product ordering under identical forecasts, budgets, supplier terms and accounting. This screen's allocation baseline is not that full replenishment benchmark.
3. Measure orders fulfilled on time, additional stock investment, ageing/expiry exposure and unresolved shortages separately. Do not hide the trade-off in an invented shortage penalty or claim profit without margin data.
4. Evaluate repeated decisions on development scenarios first. Freeze the model, comparison and acceptance thresholds before opening reserved evaluation seeds.

Reject or narrow the proposed optimisation if a competent simple rule performs just as well, improvements depend on convenient supply assumptions, or better service requires unjustifiable excess stock. Do not change customer deadlines, supplier schedules, seeds or demand patterns to manufacture a better result.

## Verification and retained evidence

All exact solves returned optimal status for their small declared models, and all decoded plans passed feasibility assertions. Five independent hand-sized tests passed: allocation versus whole-line/freshness constraints, supplier minimums plus case rounding and fees, delivery after the customer window, no-order behaviour with sufficient stock, and preventing forbidden split dispatches.

The screen took about 2.3 seconds of local computation. Retained files under `artifacts/distributor-demo/exploration/` include the protocol, reproducible scripts, five tests, all 72 assumption-case outputs and the timing profile. Input and script hashes are recorded. Additional development databases were removed after use. Production generator code, retained v2 databases and the locked Phase 2 plan were not modified. Reserved evaluation seeds remain untouched.

The exploratory solver uses the installed SciPy interface to HiGHS: [official API documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html). Mathematical optimality applies only to this stated small model; it is not a claim that the resulting decision is optimal for a real business.
