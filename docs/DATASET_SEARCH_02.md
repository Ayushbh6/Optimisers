# Dataset search restarted around target clients

13 September 2026. Governing context: [TARGET_CLIENTS.md](TARGET_CLIENTS.md). This is an initial source screen, not dataset acceptance or an optimisation result.

Immediate priority: recorded food/distributor transactions and stock/purchasing evidence relevant to Lona and Matt. A separate manufacturing candidate may address Perwanger. Do not confuse a dataset with an inventory-themed title with evidence sufficient for inventory optimisation.

| Lead | Connection to targets | Verified source information | What still blocks selection |
|---|---|---|---|
| [Iowa Liquor Sales](https://data.iowa.gov/catalog/dataset/1051) | Product/customer sales planning for a distributor; closer to Lona/Matt's business-to-business transactions than supermarket checkout data. Beverages differ from their exact assortment. | Official state-published retailer purchase records by product/date, from 2012 onward. [Federal catalogue](https://catalog.data.gov/dataset/iowa-liquor-sales-january-2012-current) explicitly links CC BY 4.0. | No demonstrated stock/receipts ledger or lost-demand evidence. Needs bounded row/schema inspection and a concrete planning decision beyond a dashboard. Do not turn wholesale purchases into consumer demand or assume spirits exhibit food expiry. |
| [FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/blob/main/README.md) | Food demand planning; relevant capability, but fresh retail differs from packaged-food distribution. | Original publisher's card provides sales, stockout indicators and contextual fields under CC BY 4.0. | Normalized sales and missing physical inventory/purchasing inputs constrain economic optimisation. Cannot present recovered demand as measured lost sales. Existing earlier review remains applicable. |
| [Grupo Bimbo Inventory Demand](https://www.kaggle.com/competitions/grupo-bimbo-inventory-demand/data) | Particularly close food-distribution setting: products, customers, depots, sales and returns. | Official competition fields include current-week sales, next-week returns and adjusted demand. Data licence is subject to competition rules. | Commercial website rights not established; rules page did not expose readable terms. Adjusted demand is not independently observed unconstrained demand. Next-week returns create a specific future-information hazard. No download or rule acceptance performed. |

First investigation priority is **Iowa's accessible distributor-sales records**, while continuing to seek richer inventory/purchase records. This is a priority for inspection, not selection of an inventory optimiser. Grupo Bimbo is closer in product domain but cannot be selected based on a convenient mirror or assumed reuse rights.

The old Iowa Socrata metadata endpoint returned HTTP 403. The current official catalogue supplies replacement schema and row endpoints at `idh-be.iowa.gov/api/v1/datasets/1051/`; access to those records has not yet been validated. No large dataset was downloaded in this restarted screen.

Manufacturing search has not yet produced a verified, commercially reusable operational dataset for Perwanger. Do not force a leather image dataset or artificial scheduling benchmark into an inventory/production claim.

Next acceptance gate: inspect a bounded sample and schema; establish the real decision, permitted claim and missing inputs; then rank through honest, valuable, standard and sellable gates. No selected replacement dataset and no implementation yet.

## Exploration result — 13 September 2026

**FreshRetailNet is the strongest currently accessible lead for a food demand-planning demo. No replacement dataset has yet passed the gates for an inventory-savings optimiser.** These are different conclusions; do not label the former as the latter. The original retail data remains unsuitable for the already-reviewed flagship claim.

### Actual file exploration

Inspected 900 daily records: ten complete 90-day store/product series, sampled at evenly spaced offsets in the training-file order. These are a coverage sample, not random selection or population estimates. Every series runs 28 March–25 June 2024. No forecasting, demand reconstruction or policy was run.

| Check in these 900 records | Finding |
|---|---:|
| Missing field values | 0 |
| Hourly arrays with wrong length | 0 |
| Daily sales differing from summed hourly sales | 0, tolerance 0.000001 |
| Stockout counts differing from hours 06:00–21:59 | 0 |
| Days with some recorded daytime stockout | 370 |
| Zero-sales days | 33 |
| Zero-sales days without recorded daytime stockout | 19 |
| Days with a discount below 1 | 697 |
| Hours having positive sales and a stockout flag | 160 |

The last row is not automatically a data error: selling earlier and running out later in the same hour is possible. Exact within-hour availability is not established. Never treat every flagged hour as 60 minutes of zero availability, or divide sales by a guessed available fraction. The sample also shows why zero sales and stockout are not interchangeable.

Source response hashes, sample method and checks are retained in `artifacts/dataset-search/food-screen/`. Only one raw series is retained, alongside a compact summary and reproducible inspector; about 57 KB total. The viewer serves a live revision, so hashes document the inspected responses rather than a pinned release. The initial batch hit a server error; the subsequent complete run returned all ten blocks successfully.

The [original data card](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K/blob/main/README.md) identifies globally scaled sales, rather than usable physical stock units. It contains no purchase-order, inbound receipt, inventory quantity, supplier lead-time, expiry-batch or cost ledger. Its 865-product description also differs from the original paper's 863; neither count has been independently checked across the full data. Do not repeat one as an audited count.

The [source paper](https://arxiv.org/html/2505.16319v1) evaluates missing-demand recovery by hiding observed sales in periods without stockouts. That is a legitimate reconstruction test, but its hidden values are created for evaluation; real missed demand during historical stockouts remains unknown. Published model improvements are not our results. Three months cannot demonstrate annual seasonality. Historical realised weather is not a weather forecast available at a past buying decision.

### Fit to the four gates

| Candidate and bounded use | Honest | Valuable | Real-world standard | Sellable | Decision |
|---|---|---|---|---|---|
| FreshRetailNet: demand planning that handles stockout-distorted sales | Pass for source; conditional for missing-demand estimates | Relevant planning capability for Lona/Matt, although fresh local retail differs from packaged-food distribution | Yes: commercial planning products account for sales hidden by stockouts | Conditional on a useful, independently evaluated planning workflow | Best accessible candidate for a forecasting/planning experiment; not an inventory-savings demo |
| Iowa: distributor product/customer sales planning | Official provenance/licence established; rows not verified here | Closer business-to-business transaction setting | Established demand-planning task | Not yet assessed beyond source description | Keep as a lead; access currently blocks exploration |
| Bimbo: food-distribution demand and returns | Real source; future-return timing needs careful handling | Strong sector fit | Established forecasting task | Commercial reuse rights unresolved | Do not download from mirrors or select until rights established |
| Bibitor: stock, purchases and sales | Does not qualify as recorded real-company evidence | Educational process fit only | Teaching model is not operational evidence | Fails intended real-data positioning | Reject for these demos |

[Lokad's demand-forecasting documentation](https://www.lokad.com/demand-forecasting/) describes handling sales censored by stockouts. Its [inventory documentation](https://www.lokad.com/inventory-optimization/) also depends on incoming and outgoing transactional flows. These support commercial relevance, not a claim that our partial dataset can reproduce the complete product or its results.

### Other source checks and exclusions

- **Bibitor:** [publisher](https://www.hubae.org/datvironment/bibitor/) describes a created teaching company in a fictional state; materials are developed from public information and have [user restrictions](https://www.hubae.org/user-restrictions/). The appealing purchase/sales/inventory tables do not make it real operational evidence. Do not confuse its many portfolio mirrors with Iowa's official records.
- **ChatGPT-generated supermarket inventory:** [publisher's card](https://www.kaggle.com/datasets/shafiirajabu/supermarket-inventory-dataset/data) explicitly says fictional. Rejected without downloading.
- **Zhao, Li and Shen's 2019 supermarket records:** [university source](https://hub.hku.hk/handle/10722/296222) describes sales, stock and replenishment for 28,757 products. Promising fields, but a working original data download and commercial data licence were not established. The paper's publishing terms are not a data-reuse licence. Keep as an unresolved source lead, not an accepted dataset.
- **Aguirregabiria supermarket panel:** a [secondary loader](https://econirl.readthedocs.io/en/latest/_modules/econirl/datasets/supermarket.html) labels it academic use; original-source rights remain unverified. Monthly aggregation also weakens order-timing evaluation. Not selected.
- **Iowa access:** both current official schema and bounded rows URLs returned HTTP 403; the old endpoint also failed. This establishes access failure in this environment, not that the public dataset has ceased to exist. No rows were downloaded and no stock claims inferred from its catalogue.
- **Perwanger:** no suitable commercially reusable manufacturing/material-flow dataset was verified in this pass. Food-demand data must not be presented as a leather-production demo.

### Recommendation and next experiment, pending decision

If one of the first two demos may demonstrate **better demand planning**, proceed with FreshRetailNet. The buyer-facing question is: “Which products need the buyer's attention because recent sales are an unreliable guide to next week's demand?” Show observed sales, recorded stockouts, forecasts and uncertainty separately. This would demonstrate a relevant component of purchasing support, not automatically recommend exact purchase orders or promise avoided waste.

Before modelling, pin the source revision and audit a larger, predetermined sample of complete series, including low-sales products and both stockout-heavy and stockout-light cases. Resolve hourly-label semantics from source code/documentation. Set a fixed historical training/validation/final-test split and a seven-day horizon. Use simple last-week and recent-weekday-average baselines plus a competent stockout-aware reference. Future realised stockouts may define evaluation coverage but must never be forecast inputs; uncertain future promotions/weather must be omitted or explicitly supplied as scenarios.

Proposed showcase gate: at least 5% lower aggregate absolute forecast error than the strongest fixed baseline, no worse overall signed bias, improvements across most weekly evaluation windows and no material collapse on low-sales products. Fix exact segmentation, bias tolerance and sample size before running. Score genuinely observed available periods separately, disclose excluded coverage, and report a separate controlled hidden-sales test. Never score estimates against other estimates as if they were facts. Failure means rejecting the proposed forecasting claim, not adjusting the threshold after seeing results.

If both first demos must demonstrate **actual stock/order decision optimisation**, do not select FreshRetailNet merely to finish the search. Continue seeking a source with the relevant operational records. We have not earned an inventory-savings claim from any replacement reviewed so far.
