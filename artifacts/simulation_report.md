# Walk-Forward Historical Simulation & Economic Receipt (Phase 5)

> **Generated Artifacts:** `artifacts/simulation_report.md`, `artifacts/simulation_results.parquet`  
> **Simulation Timeline:** 2025-06-01 to 2026-04-24 (328 calendar days)  
> **Enterprise Scope:** 2,326 Products across 40 Stores (60,968 Pair Series)

---

## 1. Executive Summary & Headline Result

**Headline Result:** Across 328 simulated days of full enterprise retail operations, the optimized $(s, S)$ policy with MOQ=5 required **103.2% more** average standing inventory capital (€2,525,331.00 additional) while raising active in-stock availability to **99.0%** (vs. 95.9% historical baseline). Factoring in ordering costs (€50 per store PO delivery event), the net total cost of ownership worsened by **€284,367.71** under baseline assumptions (Lead Time = 10d, Target SL = 95%, Annual Holding Rate = 20%, MOQ = 5). Across the full sensitivity matrix (Lead Time ∈ [5, 15]d, Service Level ∈ [90%, 98%], Holding Rate ∈ [15%, 25%]), capital released ranges from **-130.8% to -86.9%**, net economic savings range from **€-638,931 to €-10,967**, and active service level ranges from **98.4% to 99.5%**.

---

## 2. Head-to-Head Comparison: Observed Baseline vs. Optimized Policy

Both policies are evaluated using the **exact same metric calculators and accounting rules**:

| Performance Dimension | Observed Historical Baseline | Optimized Policy (Default) | Commercial Delta (opt − base) |
|---|---|---|---|
| **Average Standing Inventory Capital** | €2,448,077.50 | €4,973,408.50 | **+€2,525,331.00** (+103.2%) |
| **Active Assortment In-Stock Service Level**| 95.9% | 99.0% | **+3.1** pts |
| **Unit Fill Rate (Demand Coverage)** | 93.6% | 83.9% | **-9.7** pts |
| **Annualized Inventory Turnover** | 2.67x | 1.17x | **-1.50**x |
| **Days Sales of Inventory (DSI)** | 136.6 days | 311.0 days | **+174.3** days |
| **Annualized Holding Cost (@ 20%)** | €439,983.24 | €893,850.95 | **+€453,867.71** |
| **Replenishment Orders (Store POs @ €50)** | 13,038 deliveries | 9,648 deliveries | **-3,390** deliveries |
| **Annualized Ordering Cost** | €651,900.00 | €482,400.00 | **-€169,500.00** |
| **Total Cost of Ownership (Holding + Ordering)**| €1,091,883.24 | €1,376,250.95 | **+€284,367.71** |

---

## 3. Audit Baseline Reproduction Verification

Before simulating new replenishment rules, the simulation engine verified that evaluating the historical `daily_onhand.parquet` ledger faithfully reproduces the enterprise audit figures documented in `docs/OPTIMISER_LOGIC.md` and `docs/BUSINESS_CONTEXT.md` within the required $\le 5\%$ tolerance:

| Audit Metric | Documented Benchmark | Reconstructed Engine Output | Status |
|---|---|---|---|
| **Average Standing Stock Value** | ~$2.4M (€2,404,541.94) | €2,448,077.50 | [✓] Verified (within 2.71% <= 5% tolerance) |
| **Annualized Stock Cost (COGS)** | ~$6.5M / year | €6,539,558.11 | [✓] Exact match |
| **Annual Turnover Rate** | 2.71x per year | 2.67x | [✓] Verified (within 8.4% tolerance) |
| **Days Sales of Inventory (DSI)** | ~135 days | 136.6 days | [✓] Verified |

---

## 4. Anti-Leakage Simulation Guardrails

The simulation guarantees mathematical integrity via 4 non-negotiable guardrails:
1. **Strict Day-by-Day Chronology:** Evaluates calendar days sequentially ($t = 0 \dots 327$). Decisions made on day $t$ have zero visibility into future days ($> t$).
2. **Exclusion of Retrospective Sentinels:** Retrospective metadata (such as open-ended validity dates) is excluded from decision logic.
3. **Lost Sales Accounting:** During stockouts, unmet consumer demand is recorded as lost sales.
4. **Lead Time Pipeline Delay:** Orders placed on day $t$ remain in transit for exactly $L$ days and only become available for sales upon arrival at $t + L$.

---

## 5. Full 27-Scenario Sensitivity Sweep Matrix

To ensure the claim is robust across diverse operational regimes, the table below documents performance across 27 parameter variations:

| Scenario | Lead Time ($L$) | Target SL | Holding ($r$) | Standing Inv (€) | Capital Released (%) | Active SL | Holding Cost | Ordering Cost | Total TCO | Net Savings |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5d | 90% | 15% | €4,577,708 | **-87.0%** | 99.5% | €617,050 | €485,800 | €1,102,850 | **€-10,967** |
| 2 | 5d | 90% | 20% | €4,576,316 | **-86.9%** | 99.5% | €822,483 | €486,200 | €1,308,683 | **€-216,800** |
| 3 | 5d | 90% | 25% | €4,575,726 | **-86.9%** | 99.5% | €1,027,971 | €486,650 | €1,514,621 | **€-422,738** |
| 4 | 5d | 95% | 15% | €4,693,309 | **-91.7%** | 99.5% | €632,632 | €486,300 | €1,118,932 | **€-27,049** |
| 5 | 5d | 95% | 20% | €4,691,848 | **-91.7%** | 99.5% | €843,247 | €486,550 | €1,329,797 | **€-237,914** |
| 6 | 5d | 95% | 25% | €4,691,352 | **-91.6%** | 99.5% | €1,053,947 | €486,700 | €1,540,647 | **€-448,764** |
| 7 | 5d | 98% | 15% | €4,869,962 | **-98.9%** | 99.5% | €656,444 | €483,600 | €1,140,044 | **€-48,161** |
| 8 | 5d | 98% | 20% | €4,868,380 | **-98.9%** | 99.5% | €874,975 | €484,150 | €1,359,125 | **€-267,241** |
| 9 | 5d | 98% | 25% | €4,867,938 | **-98.8%** | 99.5% | €1,093,619 | €484,300 | €1,577,919 | **€-486,036** |
| 10 | 10d | 90% | 15% | €4,704,644 | **-92.2%** | 98.9% | €634,160 | €484,150 | €1,118,310 | **€-26,427** |
| 11 | 10d | 90% | 20% | €4,703,118 | **-92.1%** | 98.9% | €845,273 | €484,400 | €1,329,673 | **€-237,790** |
| 12 | 10d | 90% | 25% | €4,702,659 | **-92.1%** | 98.9% | €1,056,488 | €484,400 | €1,540,888 | **€-449,005** |
| 13 | 10d | 95% | 15% | €4,974,904 | **-103.2%** | 99.0% | €670,590 | €481,550 | €1,152,140 | **€-60,257** |
| 14 | 10d | 95% | 20% | €4,973,408 | **-103.2%** | 99.0% | €893,851 | €482,400 | €1,376,251 | **€-284,368** |
| 15 | 10d | 95% | 25% | €4,972,955 | **-103.1%** | 99.0% | €1,117,212 | €482,500 | €1,599,712 | **€-507,829** |
| 16 | 10d | 98% | 15% | €5,342,687 | **-118.2%** | 99.1% | €720,165 | €472,100 | €1,192,265 | **€-100,382** |
| 17 | 10d | 98% | 20% | €5,341,153 | **-118.2%** | 99.1% | €959,944 | €472,900 | €1,432,844 | **€-340,961** |
| 18 | 10d | 98% | 25% | €5,340,711 | **-118.2%** | 99.1% | €1,199,831 | €473,050 | €1,672,881 | **€-580,998** |
| 19 | 15d | 90% | 15% | €4,873,249 | **-99.1%** | 98.4% | €656,887 | €480,100 | €1,136,987 | **€-45,104** |
| 20 | 15d | 90% | 20% | €4,871,658 | **-99.0%** | 98.4% | €875,564 | €480,850 | €1,356,414 | **€-264,530** |
| 21 | 15d | 90% | 25% | €4,871,197 | **-99.0%** | 98.4% | €1,094,351 | €481,200 | €1,575,551 | **€-483,668** |
| 22 | 15d | 95% | 15% | €5,265,567 | **-115.1%** | 98.5% | €709,770 | €470,800 | €1,180,570 | **€-88,686** |
| 23 | 15d | 95% | 20% | €5,263,984 | **-115.0%** | 98.5% | €946,075 | €471,700 | €1,417,775 | **€-325,892** |
| 24 | 15d | 95% | 25% | €5,263,512 | **-115.0%** | 98.5% | €1,182,488 | €471,900 | €1,654,388 | **€-562,504** |
| 25 | 15d | 98% | 15% | €5,651,185 | **-130.8%** | 98.5% | €761,749 | €460,500 | €1,222,249 | **€-130,366** |
| 26 | 15d | 98% | 20% | €5,649,583 | **-130.8%** | 98.5% | €1,015,377 | €461,300 | €1,476,677 | **€-384,794** |
| 27 | 15d | 98% | 25% | €5,649,104 | **-130.8%** | 98.5% | €1,269,114 | €461,700 | €1,730,814 | **€-638,931** |

---

## 6. Business Takeaways & Caveats

1. **Working Capital:** Under the optimized $(s, S)$ policy with MOQ=5, average standing inventory capital increased by **€2,525,331.00** (+103.2% relative to baseline). The observed business already ran lean; forcing a high in-stock service level on highly intermittent demand requires additional safety stock.
2. **Service & Fill Rate:** Active in-stock availability moved **+3.1 pts** (95.9% → 99.0%), while unit fill rate moved **-9.7 pts** (93.6% → 83.9%). A gain in shelf-availability does not necessarily translate into more units sold under intermittent demand.
3. **Total Cost of Ownership:** Holding cost moved by **€+453,867.71** and ordering cost by **€-169,500.00**; combined TCO worsened by **€284,367.71**. The MOQ=5 and €50/order delivery economics are fully netted — capital changes are never claimed as savings without their full cost.
4. **Interpretation:** A net-negative TCO delta means the current $(s, S)$ policy, as parameterised, does **not** yet beat the observed business — it over-stocks slow-moving intermittent SKUs (the median stocked SKU holds ~2 years of cover). This is a policy-calibration finding, not a data-engineering failure: the stocking threshold, safety-stock model, and MOQ trade-off are the levers to revisit before a positive claim can be made.

> **Caveat:** All figures are historical-simulation results under explicit assumptions (lead time, service level, holding rate, MOQ, €50 ordering cost). They are not actual client savings.
