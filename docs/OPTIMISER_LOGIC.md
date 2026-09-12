# Optimiser logic

> Plain-language working notes. Current status: Part 1 final review passed, including all 27 full-data settings. Part 2 has not started.

We are building a decision system for a 40-store retailer. It should turn messy sales and stock exports into a traceable answer to two questions: how much stock should a store hold, and when should it reorder?

The useful product is a decision with a receipt. The receipt shows which records were used, what was estimated, what the rule decided, what happened in a day-by-day replay, and which financial figures are unavailable. It is not a promise of a saving before the evidence exists.

## The five steps

```text
raw records
  -> separate purchases, returns and stock evidence
  -> estimate demand using information available on each day
  -> forecast rare sales
  -> calculate a reorder recommendation
  -> replay recorded purchases and report the result
```

The current Part 1 runner is:

```text
python -m src.build_part1 --output-dir PATH
```

It writes fresh outputs and a manifest with input hashes, settings, code revision and dependency versions. It does not read old files from `artifacts/`.

## What the data means

The sales file records purchases and returns. Gross purchases measure the customer purchase stream. Returns are kept separate and are added back to physical stock at day end. A return must never lower the purchase demand used for forecasting.

The inventory file records date intervals and quantities. The causal stock estimate starts from a snapshot when one is available, then moves forward through purchases and day-end returns. A later snapshot can explain an adjustment at its own date, but cannot rewrite an earlier estimate. Unknown stock stays unknown. Negative raw quantities remain visible while the physical estimate is floored at zero.

The expanded interval view is a historical reference for accounting. It is not a forecast input because its ending date may only be known later.

## Demand and forecasting

Most product-store pairs sell rarely, so a single pair has little evidence. Croston and TSB are simple methods that learn how often a rare sale happens and its typical size. We pool products within a subcategory and store, then split the group estimate using observed shares.

An empty shelf can hide purchases. We therefore produce an **estimated demand** value using prior in-stock rates and record the availability assessment, fallback and information cutoff. This is an estimate, not verified true customer demand. The replay does not treat estimated missed customers as observed purchases.

Model fits use completed Monday-to-Sunday weeks only, excluding incomplete leading and trailing weeks for each product-store pair. Product shares update daily using all history through that day, including the current incomplete week. Category facts are dated and pair-local. Each snapshot records the history cutoff, forecast start, method, units and the fact that its uncertainty bounds are an approximation. A forecast does not need to beat a benchmark for the pipeline to be correct; its inputs and dates must be traceable.

## Reorder and replay

The current policy keeps the agreed starting settings: ten-day lead time, 95% nominal service target, 20% annual holding rate, minimum order quantity five and the existing stocking threshold. A missing pair cost makes the recommendation unavailable; the code does not invent a substitute cost.

The replay runs each day in this order:

```text
opening stock
  -> scheduled arrivals
  -> recorded purchases fulfilled from available stock
  -> day-end returns
  -> closing stock
  -> next forecast and reorder decision
```

When the stock position reaches the reorder point, an order fills the gap to the existing order-up-to target, subject to the minimum quantity. Excess stock is never deleted when a target falls. Orders are whole units and remain outstanding after the replay ends, with exact due dates retained. After initial historical learning, the same demand estimator learns from the simulated shop’s own fulfilled purchases and shelf availability. A day that empties the shelf is excluded from available-day training even if returns replenish stock at closing. The forecaster sees only fulfilled purchases and stock availability from the simulated shop. It cannot see unfulfilled targets or later retailer sales.

## What can be reported

The main service measure is observed-purchase coverage: fulfilled recorded purchases divided by recorded purchases. The historical reference is 100% by construction for its recorded target; that does not measure the retailer’s true customer fill rate.

Both sides are valued on identical pair-days using the same dated cost. Unknown reference stock or missing costs exclude that pair-day from both capital figures. First 15 days and the remainder are shown separately. All 27 sensitivity settings receive independent copies of initial learning and use their own holding rate on both sides. Reports show coverage, unfulfilled units, stock held, orders, reference stock coverage and cost coverage on matched scopes. Simulated ordering cost is shown separately as an assumption. Historical ordering cost and total-cost savings are unavailable until defensible historical purchase-order records exist.

## Direction for Part 2

The dataset decides which problem we can honestly optimise. We should not force one dataset to demonstrate replenishment, allocation, forecasting and markdowns when it lacks the evidence for some of them.

```text
available records
  -> decisions those records can test
  -> strongest useful optimisation
  -> honest result and clearly limited claim
```

For this dataset, Phase 2 first ranks store stocking/replenishment, forecast selection, cross-store reallocation and slow-stock/markdown prioritisation. It then tests only the strongest opportunity in a bounded feasibility pass. Another properly sourced dataset may support a different website demo. The result here may be positive, neutral or negative; the point is true optimisation of the problem the data can actually measure.

## Verified Part 1 result

The final review is recorded in [PART1_FINAL_REVIEW.md](PART1_FINAL_REVIEW.md). The current rule fulfils about 97.18% of eligible recorded purchases and holds more valued stock than the reference on the same measured scope. That is an honest negative result for the current rule. The repaired measurement pipeline is ready for Part 2; the website savings statement is not supported.
