# Phase 2 — Choose the right optimisation before building further

> Updated 12 September 2026. Part 1 is signed off and the dataset source is confirmed. The bounded feasibility check has not yet run. Full implementation waits for its conclusion and the user's decision.

## 1. Goal

Determine which useful optimisation problem this dataset can honestly demonstrate, whether that result is strong enough for the website, and whether another dataset is needed for different claims.

```text
Treat the dataset as the source of truth
→ rank the decisions its fields can support
→ test the strongest opportunity honestly
→ build that demo, obtain missing records, or use another dataset for that claim
```

The current policy holds more stock on the matched comparison scope and fulfils 97.18% of eligible recorded purchases. That shows this policy performs poorly. It does not prove the data is useless or that a better policy will succeed.

Success for this first check is a supported decision about what this dataset should be used to optimise. It does not need to carry every future website demo. A clear reason to use another dataset for a particular claim is a valid result.

## 2. Confirmed dataset source

- **Repository:** Mendeley Data — *Retail Transactions and Stocks Data*
- **Contributor:** Jimmy Smith
- **Published:** 27 April 2026, version 1
- **DOI:** `10.17632/27x8mjm8k4.1`
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Source page:** `https://data.mendeley.com/datasets/27x8mjm8k4/1`

The publisher describes the records as daily sales and SKU on-hand data from a retail business, trimmed to a stratified ML-ready sample of 40 storefronts, 2,326 SKUs and three divisions. Those defining counts and the four-level product hierarchy match the local files exactly. We may reuse and adapt the data with attribution under CC BY 4.0.

The public record does not name or independently verify the retailer. Public wording should therefore say **“a published retail-business dataset”** or **“an anonymised retail dataset published on Mendeley Data”**, not claim a named client engagement.

## 3. Boundaries and effort limit

- Work directly, without subagents or handovers.
- Reuse `artifacts/part1-final/`, including its existing 27 sensitivity results. Do not repeat Part 1 or its full sweep.
- Complete one evidence review, rank at most four optimisation opportunities and run one small experiment round on the strongest opportunity. Use a proposed maximum of 90 minutes for the feasibility pass, including research and computation. This limits effort; it does not guarantee that missing evidence can be resolved.
- Before computation, record the exact candidates, subset, dates and run count. Time a small representative case and estimate remaining work. Reduce scope or report unresolved questions if the work exceeds the limit.
- Test at most three simple approaches for the selected opportunity, followed by at most two assumption checks on the most promising approach. No broad parameter search, repeated tuning until something wins, or new seasonal model.
- Stop experiments early if a missing fact already blocks the selected claim. Computation cannot recover missing historical orders or other absent operational records.
- At the limit, deliver findings and a recommendation. Do not silently extend the work into full Phase 2. Control token expenditure through bounded work and concise updates; do not claim precise task-level token accounting unless available.

## 4. Check A — What does the data actually establish?

Read the source definitions, existing audit and accepted outputs. Calculate only what remains unanswered.

- [x] Confirm the publisher, source page, DOI and licence. The source describes retail-business data trimmed into an ML-ready sample and permits reuse with attribution under CC BY 4.0. Do not present it as a named or independently audited retailer engagement.
- [ ] Establish what one product identifier represents: a sellable size/colour item or an aggregate. Check that stock and purchases use compatible units and store definitions.
- [ ] Verify currency and the meaning of costs and prices. Do not assume that a realised transaction price is the future selling price.
- [ ] Summarise usable stock anchors, reference-stock gaps, dated cost coverage, discrepancies and excluded purchases, by store and division. Include both product-day coverage and the share of purchases represented.
- [ ] Assess reliance on estimated shelf availability. Part 1 found that 97.6% of donor days use forward-estimated stock; these are not verified daily shelf observations.
- [ ] Inventory the available and missing business records: purchase orders, receipts, supplier delays, opening orders, transfers, adjustments, missed customers, product availability decisions and operating costs. Explain which missing records block which claims.
- [ ] Assess whether the 99-day replay can reveal useful improvement given inherited starting stock. Reduced ordering does not instantly release cash already tied up in stock. Do not invent disposal or immediate liquidation.
- [ ] Define the usable comparison scope through data-quality rules before inspecting candidate outcomes. Show excluded products/stores and the share of purchases represented. A small clean subset cannot support a full-chain claim.

**Output:** known fact → uncertainty or missing fact → effect on the claim → possible remedy.

## 5. Check B — Which optimisation fits this dataset?

Rank the available problems by how directly the recorded fields can test the result. Do not force every feature into this dataset.

| Possible demo | What the data provides | Current position |
|---|---|---|
| Store stocking and replenishment | Sales, stock, costs, hierarchy and stores | Strongest candidate. Potentially testable as inventory held versus recorded-purchase coverage. |
| Forecast-method selection | Dated recorded purchases and causal history | Directly testable. Useful as part of the product, although likely weaker as the only website demo. |
| Cross-store stock reallocation | The same SKUs across 40 stores with different demand and stock | Opportunity can be measured. Transfer execution and savings require assumed transfer time/cost because transfer records are absent. |
| Slow-stock and markdown prioritisation | Stock status, selling prices, sales types and inventory history | Candidate identification is possible. Causal claims that a markdown increased sales are not supported by one observed history. |
| Actual retailer total-cost savings | Purchase orders, receipts, real delays, transfers, missed demand and operating costs | Not supported by this dataset alone. Use another dataset or obtain those records. |

- [ ] Score each candidate on data support, customer value, strength of evaluation and missing assumptions. Select one primary use for this dataset before experiments.
- [ ] State what is directly measured, what is a simulation and what requires another dataset.
- [ ] Draft the exact conditional website sentence for the selected demo before choosing a favourable result. Do not invent a percentage or imply that the result exists.
- [ ] Include the Mendeley attribution and DOI in the eventual case study.

Example structure, not an achieved result:

> “In a historical simulation covering [scope and dates], this policy held [X%] less average inventory value than the recorded reference and fulfilled [Y%] of recorded purchased units, assuming [key conditions].”

This is one possible structure for a replenishment demo. Forecast selection, allocation or markdown prioritisation require their own result-specific wording. If no qualified statement is useful enough, keep this dataset for the capability it genuinely supports and choose another verified dataset for the stronger claim.

## 6. Check C — Which assumptions are defensible?

For each consequential assumption, record its reason, supporting source or operator evidence, plausible range and effect on the conclusion. Generic industry practice can justify a scenario; it does not establish this retailer's actual operation.

- [ ] Review lead times, minimum orders, ordering charges, holding rate, returns, opening orders and forward stock movement.
- [ ] Separate assumptions that make a transparent simulation possible from facts needed to compare with the real business. An assumed order charge cannot reveal historical ordering cost.
- [ ] Identify the two uncertainties most likely to reverse the result and prioritise them for the limited assumption checks.
- [ ] Explain what a later missed-demand trial would require: candidate and comparator face the same explicitly hypothetical customer demand and starting conditions. Do not treat historical stock as the known counterfactual under invented additional customers.
- [ ] Reject assumptions chosen to produce attractive results: free instant supply, erased excess stock, zero costs for relevant work, future retirement dates, or invented demand presented as observed fact.

**Output:** a small assumption register and a clear boundary between a simulated result and real-world savings.

## 7. Check D — Is the strongest opportunity worth pursuing?

Run this only if Checks A–C leave a useful claim worth pursuing.

First complete the opportunity ranking. If store stocking and replenishment wins, inspect the saved ledger and sensitivity results and explain what drives excess stock: inherited inventory, forecast levels, stock buffers, minimum orders, stocking eligibility or their interaction. If another opportunity ranks first, define an equally bounded experiment whose outcome is observable in this dataset. Distinguish measured causes from hypotheses.

- [ ] Freeze an affordable representative subset using historical information and declared data-quality rules. Cover different stores and sales rates; disclose limitations. Keep forecast pooling free of future purchase information.
- [ ] Before new results, record numerical screening requirements for recorded-purchase coverage, worthwhile inventory reduction and adequate comparison coverage. These are business decision criteria, not correctness-test assertions. Do not weaken them after poor results.
- [ ] Test at most three simple alternatives for the selected opportunity. For replenishment, options include historical-average forecasts, last-completed-week forecasts or a simpler stock target. Specify each rule once and reuse shared causal contracts.
- [ ] For replenishment, compare alternatives with both the current policy and recorded reference on identical scope and dates. For another opportunity, predeclare the appropriate simple baseline. Beating our poor policy alone does not demonstrate improvement over the retailer.
- [ ] Preserve the causal information boundary appropriate to the selected experiment. For replay, fulfilled purchases and the shop's own availability feed future decisions; retain whole-unit stock, dated costs, exact delays, pending orders and stock conservation.
- [ ] Report all measures needed to understand the trade-off. For replenishment this includes coverage, unfulfilled units, average inventory value, ending stock, outstanding orders, assumed holding costs and simulated ordering costs, with the first 15 days separated. Keep historical total-cost savings unavailable where historical orders are unknown.
- [ ] Run at most two predeclared assumption checks on the most promising alternative. If the result reverses, report its dependence instead of searching for friendlier settings.
- [ ] Save all attempted settings and results, including failures. Reproduce the selected small result once if it is used to justify proceeding.

The existing June–April data have already informed development. An earlier/later split can limit additional tuning, but cannot turn inspected data into an untouched final test. These experiments establish feasibility only. Stronger validation needs new data or a genuinely independent evaluation.

## 8. Decision — Build here, add another dataset, or obtain records

| Decision | Required evidence | Next action |
|---|---|---|
| Build this dataset's strongest scoped demo | Source rights established, usable scope, a simple alternative meets predeclared screening criteria, and the conclusion survives the selected assumption checks | Present the attainable claim and bounded implementation proposal for the user's decision. |
| Obtain specific records first | A named missing fact blocks the claim and there is a realistic route to obtain it | Specify necessary fields and what they unlock. Pause model development. |
| Add or switch datasets for a different demo | Inadequate evidence for that claim or no worthwhile signal within the bounded check | Keep the useful work from this dataset and find evidence matched to the next optimisation problem. |

Three unsuccessful alternatives do not prove that no optimiser can work. They support a practical stop decision for our limited budget. A good small replay likewise does not guarantee real operating savings.

If another dataset is recommended, use the remaining feasibility budget to shortlist at most three sources for the specific missing demo. Verify publisher, licence, availability and actual fields. Prefer connected sales, inventory, receipts/orders and cost records for a true replenishment-savings claim. Distinguish real data from synthetic benchmarks. Do not download large datasets or build new adapters during this pass.

## 9. Full implementation after a go decision

The feasibility conclusion determines the implementation scope. These are conditional workstreams:

1. Implement only the selected dataset-appropriate optimisation through shared contracts. Consider seasonality only where supported; eleven months cannot establish repeatable annual patterns.
2. Add economic stocking decisions only when costs, prices and operational consequences are defensible. Improve uncertainty calculations where the evidence supports them.
3. Select settings on declared development data, freeze the rule and evaluate on appropriate independent data. Keep hypothetical missed-demand trials distinct from recorded-purchase replay.
4. Verify the final result at the justified scope, including operational assumptions, service trade-offs and matched accounting. Obtain an independent review before publishing numerical savings claims.

Do not start these workstreams merely because Part 1 passed. First deliver the ranked opportunities, feasibility decision, attainable claim and expected remaining effort to the user.

## 10. Storage, verification and completion

- Keep raw inputs in `data/raw/` and accepted Part 1 evidence in `artifacts/part1-final/`.
- Keep feasibility scripts and compact results together in `artifacts/phase2-feasibility/`. Place necessary scratch/test outputs beneath it, explicitly configure test temporary locations, and remove superseded outputs after verification. No project runs or analysis scripts in system temporary folders or Downloads.
- Retain input hashes, code/configuration identity, subset rules, periods, candidate settings, result tables and essential checks. Avoid duplicate copies of full Part 1 tables.
- Write one plain-language decision report at `docs/PHASE2_FEASIBILITY.md` and update `CURRENT_STATUS.md` when the check is executed. Do not create placeholder results now.
- Test new shared decision logic for correctness and future-data isolation. Do not rebuild the full dataset for document edits or small reporting changes.
- Keep repository rules and the frozen archive unchanged.

The feasibility pass is complete when it answers: **which optimisation best fits this data, what it can and cannot prove, which assumptions matter, what the bounded experiment found, and whether more investment is justified.** Include the ranked opportunities, exact proposed public claim for the selected demo, the role of any additional dataset, and the next action with expected effort. A favourable result is neither guaranteed nor required.
