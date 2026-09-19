# Adaptive discrete purchasing trial 02

Completed 17 September 2026. Synthetic development evidence, not client outcomes or realised savings.

## What changed

Candidate screening now commits only today's edited supplier basket and recalculates competent stock cover at every later supplier decision from that candidate's evolving physical state. This is done independently under nominal, lower, higher and four historical order-pattern views. The stock-cover reference evolves independently in the same way.

The warehouse engine still enforces dated terms, whole cases, product and supplier minimums, charges, weekly budget, capacity, freshness, expiry and customer dispatch rules. The search bounds remain eight basket lines, one-case steps, eight two-line candidates and forty total candidates. There is no shortage penalty, selling margin or weighted business score.

Five hand tests cover deterministic generation, supplier-minimum repair, exact predicted-versus-physical equality, safe adaptive deferral and cross-product weekly-budget displacement. The active suite passes **167 tests**. On the original 31 July ample-stock state, the earlier six-unit Mint Drops reduction is now rejected by the higher-demand view after 49 physical replays in 18.6 seconds.

## Frozen four-case result

The cases and source hashes were frozen before outcomes in `artifacts/distributor-demo/discrete-physical-trial-02/contract.json`.

| Family | Service change | Average stock + commitments | Customer/product regressions | Changed decisions |
|---|---:|---:|---:|---:|
| Ordinary trading | 0.00 points | -8.31% | 0 / 0 | 6 |
| Restricted spending | 0.00 points | -0.08% | 0 / 0 | 1 |
| Supplier disruption | 0.00 points | -8.20% | 0 / 0 | 7 |
| Ample stock | **-0.48 points** | -8.23% | **1 / 1** | 6 |

All accounting audits passed. The search executed 6,643 top-level physical replays and recorded 2,615.5 seconds of search runtime across 128 buyer decisions. Generated databases were removed after compact reports were retained.

## Ample-stock regression

One realised order line regressed: `F-CO-000102-L01`, 12 Nougat Bars (`PRD-020`) for `CUS-015`, created 28 July and due 31 July.

- Stock cover delivered all 12 on 31 July.
- The adaptive discrete policy delivered all 12 on 1 August: no final unit loss, but 12 fewer on-time units.
- The customer allows two late workdays and requires 60 days freshness.
- The policy skipped the 12-unit Nougat Bar orders on both 10 and 17 July, then resumed ordering on 24 July. That receipt arrived 1 August.
- Restoring either skipped order, costing €66.12 in goods, restores the 31 July delivery. These counterfactuals overlap and must not be added together.

The adaptive correction catches the earlier future-basket and budget feedback defect. It does not make unknown realised demand available to planning. In this case none of the seven declared demand views reproduced the later 12-unit customer/date requirement strongly enough to reject both consecutive removals. This is a negative coverage result, not a physical-simulator mismatch and not grounds to tune a multiplier against the known outcome.

## Decision

The commercial question is not yet answered positively. The method reduced simulated stock investment in all four development cases, but it did not protect the deliveries achieved by stock cover in the ample-stock control.

The 18-case batch is not authorised. Fresh seeds 91301–91305, website/API/import/container work and savings claims remain closed. Any next numerical proposal requires a new pre-outcome design addressing consecutive-removal exposure without using this known future order to tune a parameter.

Evidence is retained in `artifacts/distributor-demo/discrete-physical-trial-02/`: frozen contract and source archive, four compact case reports, summary, exact regression replay and the bounded restoration audit.
