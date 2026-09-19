# Exploratory opportunity review — 13 September 2026

## Recommendation

Do not give this dataset one of the website's 2–3 flagship optimisation slots on the evidence currently available. Keep Part 1 as a reusable measurement system and this dataset as supporting evidence of careful retail analysis. Move the search for a flagship demo to other public datasets, subject to the user's decision.

This is an investment recommendation, not proof that optimisation is mathematically impossible here. No alternative policy, forecast model or optimiser was built or evaluated. A narrow, explicitly assumed simulation remains possible. The exploration did not establish enough decision-specific evidence to recommend spending the next development budget on it.

The strongest directly supported work is category-level sales forecasting and slow-stock review. Both could help a planner. Neither currently demonstrates that our system chooses a commercially better stock, transfer or markdown action.

## What was examined

- The two complete raw CSV files, accepted Part 1 comparisons, forecast summaries and all 27 retained sensitivity results. No Part 1 rebuild.
- Three descriptive observation dates: 30 September 2025, 31 December 2025 and 15 January 2026. Each uses the previous 84 days and describes purchases in the following 28 days.
- Stock observations made on the observation date, within seven days, and within 28 days. These are diagnostic freshness bands, not claimed retail standards or revised plan thresholds.
- A follow-up distinction between newly observed and established product-store pairs. Established means first present in either source at least 84 days earlier. It does not prove continuous shelf availability.
- A further quality-only subset: established pair, at least three stock observations in the prior 84 days, latest observation within seven days, nonnegative latest stock and positive latest unit cost.
- Current primary-source product documentation for Inventory Planner, Nextail, RELEX, Lokad, StatsForecast and frePPLe.

The dates/windows/freshness bands were fixed before their first calculations. Established-pair and quality-subset diagnostics were added to investigate the initial findings. This is exploratory analysis, not a preregistered validation exercise. December and January follow-up windows overlap, and none is an untouched holdout.

All source records remain intact. Missing future transaction rows mean no *recorded* purchases for these descriptions, not proven zero demand. Later purchases were used only to describe cohorts; no recommendation had access to them.

Reproducible evidence: `artifacts/phase2-feasibility/explore_data.py` and `exploration.json`. The JSON records raw hashes, script hash, revision, retained-result hashes, definitions and all reported cohorts. Run with `.venv/bin/python artifacts/phase2-feasibility/explore_data.py`. The bundled analysis runtime lacks Parquet support; the existing pinned project environment supplies it. No dependencies were installed.

## 1. The dataset's actual strengths

The publisher describes a stratified retail-business sample with 40 storefronts, 2,326 SKUs and three divisions. Sales and stock have matching product identifiers and category descriptions. The raw purchases total 124,542 units; returns total 7,547 units. It is reusable with attribution under CC BY 4.0. The publisher does not establish a named client relationship or completeness of the original business's transactions. [Mendeley source](https://data.mendeley.com/datasets/27x8mjm8k4/1)

The useful strength is breadth: many products, locations, categories and dated selling/stock records. That supports comparison of business patterns, separate treatment of returns, and traceable historical analysis.

The weakness is depth at the exact level where a stock decision must happen. Across 63,556 product-store pairs in either source, 48,130 (75.7%) have at most two purchased units in the entire history. Those pairs still account for 49,672 purchased units (39.9% of all purchases). Quiet items cannot simply be discarded as financially irrelevant.

Sparse sales are common in real inventory work; sparsity alone is not a rejection reason. Here it combines with uncertain availability, incomplete operational context and a short history.

## 2. Where the selling signal is strongest

The table describes how similar sales rankings were between the earlier 84 days and subsequent 28 days. A rank association near one means rankings persisted; near zero means little association. These are descriptive relationships, not forecast accuracy results.

| Level compared | September cut | December cut | January cut |
|---|---:|---:|---:|
| Total purchases by store | 0.87 | 0.91 | 0.89 |
| Purchases by subcategory and store | 0.78 | 0.82 | 0.76 |
| Purchases by product across the network | 0.31 | 0.52 | 0.38 |
| Each product's sales shares across stores | -0.01 | 0.04 | 0.04 |

For the last row, products needed at least 20 purchased units in the earlier period. Store pairs had to be known at the observation date. Shares use the represented known pairs; rows without a defined later share are omitted from the correlation.

Broad store/category patterns persist. That could support a category planner's sales outlook. The same evidence does not establish reliable knowledge that a particular shoe should move from one store to another. Store size, availability and product lifecycle can contribute to these associations. Near-zero association does not prove a pooled or uncertainty-aware model cannot help.

Real assortment planning also connects local demand with space, product presentation and substitution. Those constraints and customer-choice records are not available here. Grouping products does not make different shoes interchangeable. [RELEX assortment planning](https://www.relexsolutions.com/solutions/assortment-planning-software/)

## 3. Slow stock: a useful warning, not a safe action

An important trap is to interpret 84 days with no purchases as a reason to stop stocking a product.

| Observation date | Later purchases from established pairs with no purchases in the preceding 84 days | All later purchases from established pairs | Share |
|---|---:|---:|---:|
| 30 September | 944 units | 2,646 units | 35.7% |
| 31 December | 1,828 units | 4,361 units | 41.9% |
| 15 January | 1,696 units | 4,033 units | 42.1% |

These cohorts were already known at least 84 days earlier, so newly introduced pairs do not explain away the finding. A large collection of individually quiet items still generates substantial later purchases. This is not a simulation of discontinuing them and is not a lost-sales estimate.

There is nevertheless a real review signal. On 15 January, among established pairs with positive stock observations no more than seven days old:

- 3,189 pairs had positive observed stock; 724 recorded a purchase in the next 28 days (22.7%).
- 1,419 of those pairs had no purchases in the previous 84 days, representing 3,080 units at their latest stock observations.
- 196 of those 1,419 quiet pairs recorded a later purchase (13.8%).

The quiet cohort therefore sold less often. That can justify a merchandiser reviewing it. It does not show that discounting or moving those units would improve profit, that they are physically old, or that 3,080 units are excess. Later purchases can come from later receipts, so dividing later sales by this stock would not establish the sell-through of those specific units.

A basic inactivity filter already identifies this pattern. A paid prioritisation product would need to beat such a simple filter at a fixed review workload and connect the reviewed items to beneficial actions. Review time and intervention results are unrecorded. Automated overstock/aging review is already established functionality in commercial planning tools. [Inventory Planner overview](https://help.inventory-planner.com/en/articles/3456738-inventory-planner-101)

**Assessment:** useful supporting analysis; insufficient differentiation and action evidence for a flagship optimisation demo.

## 4. Cross-store reallocation: narrower than the map suggests

I counted a conservative descriptive situation: an established product-store pair with positive stock and no purchases in the prior 84 days, while another established store for the same product had nonpositive stock and at least three purchased units in those 84 days. No transfer quantity, destination ranking or simulated sale was calculated.

| Observation date | Donor pairs / products with both stock observations on that date | With both observations within seven days | Within 28 days |
|---|---:|---:|---:|
| 30 September | 9 / 1 | 35 / 3 | 95 / 35 |
| 31 December | 2 / 2 | 32 / 25 | 123 / 64 |
| 15 January | 0 / 0 | 30 / 12 | 612 / 97 |

This is not an exhaustive count of all transfer opportunities. The inactivity and three-purchase definitions are diagnostic choices, not an optimised policy. Other transfer motives, dates and rules may find more cases.

However, the apparent opportunity grows substantially as older stock observations are admitted. Older observations are not automatically wrong: these files describe intervals. They simply require stronger assumptions about what remained available. The seven- and 28-day numbers use quantities at their observation dates, not verified quantities on the decision date.

The weak observed persistence of product-specific store shares adds another uncertainty. Profit also depends on protecting the donor, transfer delay, trip and handling costs, and exact sellable variants. We have no sizes, routes or transfer history.

These are real commercial decisions: Inventory Planner compares demand needs with surplus elsewhere; Nextail accounts for trips, restrictions, sizes and merchandising trade-offs. This confirms buyer relevance, not success on our data. [Inventory Planner transfers](https://help.inventory-planner.com/en/articles/2164889-transfer-orders), [Nextail transfer workflow](https://help.nextail.co/en/legacy/how-does-the-store-transfers-module-work)

**Assessment:** a transparent assumed scenario is possible, but the present evidence does not justify selecting it for the website. Missing costs alone would not forbid a scenario; unreliable stock/destination evidence is the more important concern here.

## 5. Markdown price optimisation: labels are not enough

The raw data contains genuine price variation in the recorded fields: 9,045 successive stock-price decreases greater than 5%, and 16,265 purchasing product-store pairs with multiple realised prices.

But the price-response evidence is much thinner:

- 4,722 product-store pairs have markdown/clearance purchases; the median has only one markdown selling day.
- Only 1,065 pairs have both full-price and markdown purchases.
- Even after pooling all stores, only 22 products have at least 20 units purchased at full price and 20 at markdown/clearance. This is an evidence-density check, not a universal minimum sample size.
- There are 23,651 sales rows labelled Promo but only 30 inventory rows labelled Promo. These fields cannot be assumed to form a complete promotion calendar. The mismatch need not be a data error; the concepts may differ.

We cannot distinguish price response from campaign timing, season, stock availability and product selection simply by comparing those rows. A realised transaction price says nothing about how many customers were exposed to that price without buying.

RELEX's established workflow combines campaign objectives, lifecycle dates, inventory projections and estimated price response, including category-level pooling when needed. Category pooling is legitimate; it still cannot create the missing exposure and campaign context. [RELEX markdown workflow](https://www.relexsolutions.com/resources/markdown-optimization/)

**Assessment:** reject a markdown-profit optimisation demo on this dataset. Retain price/status analysis only as context.

## 6. Replenishment and the clean-subset option

The retained Part 1 comparison covers 2,849,918 of 5,890,360 eligible pair-days with common stock/cost evidence: 48.4%. A read-only join of purchased ledger rows to their reference stock independently confirms that matched days contain 22,016 of 33,434 eligible purchased units (65.8%); this calculation is included in the retained script. The locked broad-demo 80% requirements are not met. These are coverage problems, not evidence that no alternative ordering policy can work.

The existing policy achieves 97.18% recorded-purchase coverage and holds about 79% more average stock value on the matched scope. Across the 27 retained settings, coverage is approximately 96.5–97.9%, and matched inventory value remains above the recorded reference. Beating these settings would not by itself establish commercially useful improvement.

A narrower demo is allowed by the locked plan, so I checked a subset selected using only past data quality, not policy results:

| Observation date | Qualifying pairs | Products | Stores / divisions | Next-28-day purchases represented | Share of all next-28-day purchases |
|---|---:|---:|---:|---:|---:|
| 30 September | 522 | 214 | 40 / 3 | 315 units | 3.5% |
| 31 December | 1,333 | 446 | 40 / 3 | 822 units | 12.5% |
| 15 January | 1,512 | 507 | 40 / 3 | 680 units | 10.2% |

This subset is not a newly imposed acceptance rule. Its purpose is to reveal the cost of demanding recent, repeated stock evidence. It illustrates why saying “all 40 stores” can sound broad while representing little business volume. These 28-day scope shares are not substitutes for the locked 99-day comparison measures.

Replenishment remains a valuable real-world optimisation problem. It normally accounts for lead times, order multiples, minimum quantities and supply constraints; open-source frePPLe explicitly represents these. [frePPLe supplier model](https://frepple.com/docs/current/model-reference/item-suppliers.html)

Reasonable assumptions can support an honestly labelled simulation. My recommendation is not to demand every internal record before any demo. It is that the combination of limited observation coverage, sparse local evidence and assumed supply operations makes this a weak first investment compared with a dataset selected for its decision evidence.

**Assessment:** do not run replenishment alternatives simply to salvage the existing pipeline. No claim that they must fail has been established.

## 7. Forecast selection and commercial ranking

The retained observed-purchase average absolute daily errors are 0.018844 units for the model, 0.010582 for last-completed-week and 0.014348 for historical average. Small daily numbers reflect many zero-sale days. They do not establish useful purchasing-period accuracy or business improvement.

Forecast selection can be evaluated directly against future recorded purchases. Existing open-source systems already implement established sparse-sales methods; using those methods is sensible engineering, not a differentiator by itself. [StatsForecast sparse-sales methods](https://nixtlaverse.nixtla.io/statsforecast/docs/tutorials/intermittentdata.html)

Ranked by the supportable version of each opportunity, using the plan's scale (2 strong/direct, 1 partial, 0 unsupported; a higher assumptions score means fewer unsupported dependencies):

| Rank | Opportunity | Data | Buyer value | Evaluation | Fewer assumptions | Four-gate outcome |
|---|---|---:|---:|---:|---:|---|
| 1 | Recorded-purchase forecast selection | 2 | 1 | 2 | 2 | Honest and standard; business value conditional; not enough as standalone optimisation showcase |
| 2 | Slow-stock review prioritisation | 1 | 1 | 1 | 1 | Honest risk description possible; standard; better decisions/value not demonstrated. Markdown action variant has evaluation score 0 |
| 3 | Stocking/replenishment | 1 | 2 | 1 | 0 | Valuable and standard; honest only with explicit simulation scope; showcase evidence insufficient |
| 4 | Cross-store stock reallocation | 1 | 2 | 1 | 0 | Valuable and standard; tied with replenishment but weaker practical stock/destination evidence; showcase evidence insufficient |

No total score overrules a failed gate. The replenishment/reallocation ordering is a qualitative data/evaluation tie-break, not a numerical proof. No winner is selected simply because forecasting is easiest to evaluate.

Established practice includes sparse-demand forecasting, constraint-aware replenishment, transfers that protect donor locations, and markdown planning informed by price response. Recovering unknown demand, inventing zero-cost transfers, assuming automatic liquidation or turning future price effects into observed facts would be speculative here. A sophisticated optimiser cannot repair those evidence boundaries.

## 8. Role in the website and practical next step

This dataset can honestly demonstrate: “We reconciled an anonymised retail dataset, distinguished observed facts from stock assumptions, and showed where its evidence supports or undermines proposed inventory decisions.” It could support a technical case study or discovery-service example. It should not be represented as a successful optimisation or money saved.

For a 2–3-demo website, choose a few different decisions with observable objectives and real constraints rather than forcing three features out of this one source. A simulated comparison can be credible when the assumptions are limited, both sides use them and the claim accurately describes the benchmark. Realised client savings are a separate claim.

I made a bounded public-source check of two leads, without downloading datasets:

| Source checked | Actual strength | Decision |
|---|---|---|
| Dingdong-Inc FreshRetailNet-50K | Public Parquet files; hourly sales and stockout flags, discounts and calendar/weather fields. Publisher specifies CC BY 4.0 and commercial use. | Worth screening for stockout-aware forecasting. Sales are normalised; no listed purchase-order or physical inventory-quantity ledger. It is not an automatic replacement for a money-saving replenishment demo. |
| ORTEC EURO Meets NeurIPS 2022 routing data | Industrial routing instances with real road travel times; relevant to a delivery-planning demo. | Do not select for the client-acquisition website on its current terms: instance data is CC BY-NC 4.0 even though the code is MIT. |

Sources: [Dingdong dataset fields and terms](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/blob/main/README.md), [ORTEC competition description](https://github.com/ortec/euro-neurips-vrp-2022), [ORTEC separate code/data licences](https://raw.githubusercontent.com/ortec/euro-neurips-vrp-2022-quickstart/main/LICENSE).

These checks are a shortlist, not a recommendation to download or build either. They show why switching datasets also needs an evidence and reuse-rights check.

**Next proposed work:** screen at most three accessible, commercially reusable datasets against specific buyer decisions, using a small sample/schema before any large download. Require a credible comparator and measurable objective before selecting a demo. Do not request unavailable retailer exports from the user.

## Limits and completion

No new model scores, policy results, transfer savings, markdown effects or customer-fill claims were produced. The plan's success thresholds remain unchanged. Raw inputs and accepted Part 1 outputs were not modified. No project files were written outside the repository. Intermediate console output was removed; only this report and the compact reproducible analysis are retained.

Verification: raw totals and cohort partitions reconcile. A separate standard-library CSV calculation independently reproduced the January quality subset (1,512 pairs, 680 of 6,656 later purchased units). The final script/result identity and the accepted input/artifact hashes were checked. No pipeline tests were rerun because production code was unchanged.

The broader feasibility experiment remains unrun. The exploratory recommendation awaits the user's decision.
