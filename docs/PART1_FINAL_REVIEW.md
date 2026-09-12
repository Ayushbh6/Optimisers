# Part 1 final review

Status: **signed off for Part 1 under the stated assumptions**, 2026-09-11. Part 2 has not started.

## What this review checks

Raw records → dated stock and demand estimates → daily forecasts → whole-unit replay → fair comparisons.

The approved Part 1 plan is the acceptance standard. The earlier worker sign-off and its 96.39% result are superseded. The frozen archive and REPO_RULES.md are unchanged. No Part 2 policy or model has been introduced.

## Repairs recovered from the interrupted review

- Historical demand reconstruction and simulated-shop learning now share `DemandState`. Depletion and unresolved stock discrepancies cannot dilute available-day rates. Day-end returns cannot make an earlier empty shelf look available.
- `ForecastState` fits completed Monday–Sunday weeks, while product shares update daily using the current incomplete week's transactions. It records daily, weekly and four-week units and dated category facts.
- The production controller supplies only fulfilled purchases and availability to the shop learner. The purchase targets stay in the controller. Every scenario receives an independent copy of initial learning.
- Replay and standalone policy output use the same policy calculation, including the forecast's uncertainty. Missing pair cost remains unavailable.
- Both comparison sides use identical known-reference pair-days and the same dated cost. Holding cost uses the scenario's rate on both sides; store-day batches and order lines are shown separately.
- Late anchors start comparisons the following day. Pair endings are summed once, pending orders retain due dates, and excluded earlier purchases are recorded.
- Old stage commands are thin wrappers around the shared raw-to-report build. Source hashes include local uncommitted implementation files.

## Additional fixes in this final pass

Two new tests demonstrated failures before their fixes: an invalid return flag was accepted, and cost/price facts were lost when their inventory record had no usable stock quantity. The loader now rejects invalid return flags, non-finite or fractional quantities and missing pair identifiers. Cost and price observations are carried within their pair independently of stock availability; unknown stock stays unknown.

The run now checks gross purchases and returns separately against the raw ledger. It checks raw-file hashes before and after the build and refuses to issue a completed manifest if those inputs change. A regression test confirms that refusal. Public contracts in the recovered modules have type hints. Forecast evaluation uses the configured product-share smoothing assumption.

## Requirement evidence

| Plan area | Implementation and verification |
|---|---|
| A1: one reproducible run | `RunConfig`, thin stage wrappers, fresh-directory rejection, source/input hashes and dependency versions; raw mutation test and two identical raw-fixture builds |
| A2: purchases, returns and facts | Strict source validation, separate purchase/return totals, pair-local dated metadata/cost/price, retained raw accounting values; full source reconciliation |
| A3: reference versus causal stock | Reference interval endings stay outside decision contracts; closing snapshots, forward movement, shortage and adjustment fields; future-ending and timing tests |
| A4: prior-day demand rates | Shared `DemandState`, minimum seven available days, unchanged fallback order, estimated exposure counts, purchase floor and prior-day rate cutoff |
| A5: daily forecasting | Shared `ForecastState`, complete-week fits and daily shares, corrected interval counting, dated metadata, labelled horizons; benchmark targets and approximate coverage kept separate |
| B1: shop feedback boundary | `ShopForecaster.observe` accepts fulfilled purchases and shelf evidence only; production test changes hidden targets without changing forecasts/orders |
| B2: stock movements | Shared movement function, one-time late activation, actual MOQ and calendar delays, no stock disposal, pending orders; independent full-ledger balance and arrival checks |
| B3: existing policy | Shared `build_asof_policy_snapshot`, dated cost, eligibility and daily reasons; production order-up-to test |
| B4: fair accounting | `compare_stock`, `replay_breakdown`, `pending_orders`, identical scopes and holding rates, startup/remainder split; all 27 settings validated on the full dataset |

The raw evidence supports closing-stock timing: among 8,580 consecutive-day snapshot decreases, 5,286 match same-day net purchases, compared with 2,539 matching previous-day net purchases. This supports the assumption; it does not turn every unexplained stock movement into a known delivery.

## Acceptance evidence

The final fresh run is `artifacts/part1-final`, using schema `part1-v2`. It completed all 27 full-data settings. The final complete test suite passed 54 tests (`artifacts/part1-final/verification/part1-final-suite.log`). A separate raw-to-report repeat produced byte-identical copies of all 11 numerical Parquet outputs common to both runs; the final verification record is `artifacts/part1-final/verification/part1-final-independent-signoff.json`. The raw-fixture reproducibility test builds every stage twice into separate empty directories and compares every Parquet table exactly.

The independent audit recalculated the main ledger movements and valuation from saved files. It checked every declared artifact hash, unchanged raw files and source identity. It also compared the independent default-setting replay inside the sweep with the main replay: service, capital, holding cost, order batches/lines, ending stock and pending units agree to numerical precision.

| Check | Verified result |
|---|---:|
| Raw transaction rows | 125,751 |
| Gross purchase units / returned units | 124,542 / 7,547 |
| Daily stock and demand rows | 14,635,042 each |
| Replay rows / eligible pair-days | 6,151,308 / 5,890,360 |
| Stock-balance failures | 0 |
| Eligible purchases / fulfilled units | 33,434 / 32,492 |
| Observed-purchase coverage | 97.1825% |
| Excluded pre-anchor purchase units | 378 |
| Ending stock / pending order units | 283,392 / 2,565 |
| Full-data sensitivity settings | 27 |
| Artifact hashes independently checked | 14 |

On the matched known-reference/cost scope, average simulated capital is EUR 4,486,594 versus EUR 2,502,047 reference. The current rule therefore does not demonstrate lower capital while preserving recorded purchases. These are partial matched-scope figures, not full-chain totals.

The independent audit summary is `artifacts/part1-final/verification/part1-signoff-audit.json`; its verifier is `artifacts/part1-final/verification/verify_part1_signoff.py`. The retained set contains `acceptance_checks.json`, `run_manifest.json`, `part1_report.md` and the stock, demand, replay and summary evidence needed for Phase 2. No legacy artifact was read by the build.

The accepted entry points are the shared raw-to-report command and its stage wrappers. Older historical engine/baseline helpers remain outside that execution path. All numerical results above replace the older worker-run figures.

## Remaining product limits

The output measures recorded-purchase coverage, not the true customer fill rate. Stock between snapshots assumes no unobserved receipts. Opening purchase orders are unknown and initialised as empty. Historical returns are an external day-end stream, not linked to simulated sales. The uncertainty calculation is an approximation, including independent-day scaling. Capital comparisons cover matched known-reference/cost pair-days, not full-chain capital. Historical ordering cost and total-cost savings remain unavailable.

Part 2 still requires better policies, realistic missed-demand trials, resolved operational assumptions and independent validation before any website savings statement.

## Output consolidation

The lean accepted evidence now lives in `artifacts/part1-final/` inside the repository. All 14 original output hashes were verified again during relocation. The independent repeat and earlier temporary builds were deleted. After sign-off, `forecast.parquet`, `policy.parquet` and `forecast_benchmark_detail.parquet` were pruned because they are reproducible and are not needed for the bounded Phase 2 work. Their hashes remain in the manifests, and `cleanup_record.json` records their removal. Historical paths within the verification files describe the original execution locations.
