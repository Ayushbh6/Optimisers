# Recorded-purchase replay

`src.simulation.replay` replays the recorded purchase stream day by day. The order is opening stock, arrivals, recorded purchases fulfilled from available stock, day-end returns, closing stock, then the next decision.

The forecast history receives only fulfilled purchases and stock availability from the simulated shop. Unfulfilled purchase targets and later retailer records are not available to it. Orders are whole units, respect the minimum quantity, arrive after the configured calendar delay and remain visible when the window ends.

The main service measure is observed-purchase coverage: fulfilled recorded purchases divided by recorded purchases. Historical reference coverage is 100% by construction for its recorded target and is not a true customer fill rate.

Historical order records are missing, so historical ordering cost and total-cost savings are unavailable. The report may show simulated ordering cost as a separate assumption, together with stock and cost coverage.

Build the complete replay through:

```text
python -m src.build_part1 --output-dir PATH
```
