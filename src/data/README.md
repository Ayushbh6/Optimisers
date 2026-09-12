# Data reconstruction

`src.data` reads the raw sales and inventory CSVs and builds daily stock evidence. Purchases and returns stay in separate columns. Purchases reduce physical stock; returns are added at day end.

The output contains both a historical reference view and a causal stock estimate. The causal estimate uses snapshots and earlier stock movements only. Unknown stock, raw negative values, unexplained shortages and later snapshot adjustments remain visible.

Use the shared runner for a complete build:

```text
python -m src.build_part1 --output-dir PATH
```

The runner writes `daily_onhand.parquet` beneath `PATH`; it does not read legacy artifacts.
