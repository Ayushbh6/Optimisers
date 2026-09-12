# As-of demand forecasting

`src.forecast.asof` builds a forecast from the history supplied by its caller and filters that history to the information cutoff. It uses completed Monday-to-Sunday weeks, retains the existing Croston/TSB methods, and records the forecast start date, units, method and uncertainty label.

The uncertainty range is a normal approximation. It is a diagnostic and is not a calibrated 95% promise. Forecast correctness means that the input history and dates are traceable; it does not require the forecast to beat a benchmark.

Build it through the shared runner:

```text
python -m src.build_part1 --output-dir PATH
```

The resulting forecast artifact is a set of dated snapshots beneath the selected run directory.
