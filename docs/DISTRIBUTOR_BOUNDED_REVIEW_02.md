# Additional basket-rule test — 16 September 2026

## Scope fixed before results

Keep the replacement rule from review 01 unchanged. Test all four supplier order weekdays across 19–22 and 26–29 May 2025: eight dates outside the original June examples. Read the retained synthetic operational database at each before-ordering boundary. Review up to eight baseline purchase lines per date, in stable order, with no parameter search or evaluator access.

An edit removes one current line and, if necessary, meets the supplier minimum by topping up an already ordered line at least additional cost. Other baseline future purchases remain fixed. Current prices, cases, minimums, forecast, 60-day incoming freshness assumption, budget and physical dispatch remain unchanged.

This is additional development testing on the same scenario history, not independent held-out evidence. Each date starts from its historical snapshot; it is not a simulation of repeated purchasing decisions under the revised rule.

## Complete results

| Date | Edits checked | Surviving edits |
|---|---:|---|
| 19 May | 2 | None |
| 20 May | 3 | None |
| 21 May | 4 | None |
| 22 May | 4 | Omit 12 Nougat Bar units: €66.12 lower goods spending and nominal average investment |
| 26 May | 2 | None |
| 27 May | 3 | None |
| 28 May | 0 | Baseline already makes no purchase; retain no order |
| 29 May | 5 | Omit 12 Nougat Bar units: €66.12 lower goods spending and nominal average investment |

All 23 eligible edits were reviewed; none was excluded by the cap. Twenty-one failed the existing conditional acceptance checks. Both survivors preserved line-level deliveries in nominal/lower/higher demand projections and in four additional historical request patterns each. Historical-pattern checks also found no increased expiry or terminal stock/commitments, and no ledger errors. Source and database hashes remained unchanged.

The two surviving baskets simply omit an unnecessary product line; no compensating top-up is needed in these cases. These examples extend the rule beyond the original Honey Drops supplier basket, but the benefits are modest. **Do not sum the two €66.12 figures:** the dates and projected horizons overlap, and the later snapshot does not inherit the earlier edited decision.

## Decision

There is a repeatable conditional opportunity to review unnecessary lines in supplier baskets. We have not shown that the rule improves eight-week realised outcomes, meets the original release gate, or supports a savings headline. This result warrants a small, predeclared repeated-decision test next, with both policies evolving independently from the same initial state. It does not justify another broad tuning batch or declaring the demo ready. No further test starts automatically.

No numerical implementation changed in this test set. Previous engine-test evidence remains applicable; new run verification checks fixed dates, complete scope, input/source identity and all eight pattern checks. All results, including rejections, are in `artifacts/distributor-demo/bounded-review-02/results/`. The source archive and reproduction script are retained; no temporary database copies were created.

Reproduce from the repository root into a new directory:

```sh
PYTHONPATH=. .venv/bin/python artifacts/distributor-demo/bounded-review-02/reproduce.py --output artifacts/distributor-demo/bounded-review-02-repeat
```
