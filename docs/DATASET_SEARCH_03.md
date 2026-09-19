# Wider search: two Terra agents and source inspection

13 September 2026. User authorised two GPT-5.6 Terra agents for wider research and explicitly confirmed that credible Kaggle datasets are welcome. This round followed [TARGET_CLIENTS.md](TARGET_CLIENTS.md). No model or optimiser was implemented, and no third parties were contacted.

## Concrete new lead: a wholesale inventory dataset on Kaggle

[Underwear Data with 11 Tables & up to 100K+ rows](https://www.kaggle.com/datasets/hserdaraltan/underwear-data-with-11-tables-and-up-to-100k-rows), published by hserdaraltan. The publisher says this is a subset of a real wholesale company's database, translated, corrected, anonymised and partially imputed. This is a publisher provenance statement, not independent confirmation from a named company. The Kaggle metadata declares **CC BY-SA 4.0**; adaptations would require attention to its attribution/share-alike terms. No separate company release or imputation map was found.

Downloaded the approximately 1 MB archive into memory and inspected all eleven CSV tables. No archive or raw customer/employee tables were retained. A small JSON audit records archive hash, tables, fields and basic checks in `artifacts/dataset-search/food-screen/wholesale_source_inspection.json`.

| Actual table | Rows |
|---|---:|
| Sales order lines | 105,757 |
| Customer orders | 2,286 |
| Inventory transactions | 20,951 |
| Purchase orders | 232 |
| Products | 4,183 |
| Customers | 225 |
| Suppliers | 2 |

Sales order dates span 10 July 2003–20 April 2006. All sales lines link to existing order and product identifiers. Inventory transactions contain quantities ordered, received and missing, a transaction date, purchase-order reference and unit purchase price. Purchase-order headers have supplier and order date.

This is meaningfully richer for purchasing/stock research than sales-only data, but there are substantial unresolved issues:

- 3,345 inventory rows lack a purchase-order reference; these could include opening stock or other movements, but that meaning is unverified.
- 1,151 inventory rows lack a unit purchase price; one transaction date is missing or invalid.
- Shipment dates extend back to 2001 while sales order dates start in 2003. That flags a chronology problem; it does not establish how many orders are affected or authorise correcting them.
- Inventory has one transaction-date field; whether it dates the order, receipt or adjustment must be established. Do not calculate supplier lead times until that is clear.
- No directly named on-hand quantity snapshots, expiry records, production-resource constraints or unfulfilled-demand records were found in the exposed schemas.
- Partial imputation has no field/row flags. If it affects central timing/quantity evidence, a strong historical comparison may be impossible.

**Target fit:** transferable wholesale purchasing and inventory decisions, especially Matt's non-food assortment; an indirect analogue for Lona. It is not food expiry data, and clothing wholesale does not establish Perwanger's manufacturing process.

**Recommendation:** a bounded ledger/chronology audit is worth considering before further forecasting work. This is not yet selection of the first demo. Test whether received quantities and dated shipments can reconstruct plausible stock without invented opening balances, whether dated costs are usable, and whether meaningful purchase/receipt timing can be identified. Report discrepancies without adjusting records to get a desired outcome. Reject if imputation or ambiguous movement timing dominates. No policy comparison until this passes.

| Gate | Current verdict |
|---|---|
| Honest | Conditional: publisher claims real source; imputation and chronology need audit. |
| Valuable | Relevant wholesale purchase/stock decisions; no demonstrated improvement yet. |
| Real-world standard | Linked purchases, receipts and sales resemble operational inputs. |
| Sellable | Conditional: an old, adjacent-sector dataset needs especially clear provenance and claim limits. |

## Agent findings

**Food agent:** [Zhao, Li and Shen's supermarket source](https://onlinelibrary.wiley.com/doi/10.1002/nav.21957) exposes five supporting XLSX links, according to the agent's page inspection. This advances the earlier description-only lead: supporting files are hosted. It does not establish commercial reuse permission. No explicit data licence was found; no files were downloaded. The root's page fetch failed, so hosted-file availability is agent-verified rather than independently rechecked here.

The agent also found [Rekik et al.'s grocery inventory-record study](https://doi.org/10.1111/jbl.70079): highly relevant daily stock, replenishment, sales and physical audit records, but no publicly released underlying dataset was established. A research paper reporting real data is not itself a downloadable operational dataset.

**Manufacturing agent:** [Industrial Production Time-Series Dataset from a Beverage Bottling Line](https://zenodo.org/records/18146866) is an original, explicitly CC BY 4.0 source with real machine-output/downtime records, July 2022–February 2023. Root independently verified the source description and licence. It lacks customer orders, material inventories and routing/resource alternatives needed for the proposed scheduling/materials optimiser. Keep only for a narrower capacity-analysis possibility; it is not a Perwanger-like optimisation demo by itself.

[Production Analysis with Process Mining Technology](https://figshare.com/articles/dataset/Production_Analysis_with_Process_Mining_Technology/12697997) has an accessible 1.44 MB archive of production process records. Root checked the original metadata: its licence is labelled “4TU General Terms of Use.” Commercial rights remain unresolved; no archive was downloaded. [SME-Manufacturing-Dataset](https://github.com/HumanCenteredTechnology/SME-Manufacturing-Dataset) is another real-machine-record lead, but its research/education wording and absent clear commercial licence block selection.

## Kaggle checks and final ranking

Kaggle is accepted as a source platform. The root checked publisher descriptions through Kaggle's public API. Cacau Prime Foods and Retail FMCG Sales 2024 explicitly say synthetic. Dairy Goods Sales describes intentional modification without establishing auditable operational provenance; Country Delight-labelled data cites public information/reports rather than a verified company release. None earns real-company status from its name or licence label alone. Grupo Bimbo rights remain unresolved; a paper about it having a CC licence does not license the dataset.

For the next investigation: **(1) wholesale ledger audit**, **(2) retain FreshRetailNet for a demand-planning scope**, **(3) keep Zhao as an unresolved reuse-rights lead**. No new candidate yet passes all four gates for an inventory-savings headline. Do not change the domain or loosen evidence requirements simply to declare the search successful.
