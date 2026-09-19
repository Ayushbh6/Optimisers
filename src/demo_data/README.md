# Distributor demonstration data

This package builds **synthetic demonstration data, not client records**. It creates a connected packaged-food distribution history and keeps future evaluation events in a separate database.

```text
python -m src.demo_data generate \
  --family supplier_disruption --seed 1101 \
  --output artifacts/distributor-demo/default

python -m src.demo_data validate \
  --operational artifacts/distributor-demo/default/operational.sqlite \
  --evaluator artifacts/distributor-demo/default/evaluator.sqlite

python -m src.demo_data export \
  --operational artifacts/distributor-demo/default/operational.sqlite \
  --as-of 2025-07-06 \
  --output artifacts/distributor-demo/snapshot-2025-07-06

python -m src.demo_data suite \
  --output artifacts/distributor-demo/development-suite
```

Commands refuse to replace existing output. Evaluation seeds are reserved and the generator rejects attempts to build them during database development. The planner-facing interface is `snapshot()` or `export_csv()` against `operational.sqlite`; never give a planner `evaluator.sqlite`, regeneration configuration or hidden future events.

The daily sequence is fixed:

```text
expiry → supplier notices and receipts → new customer orders
→ scheduled stock review → dispatch → overdue cancellation → closing balance
```

The history ordering rule is deliberately simple and documented in `HistoryEngine._place_orders`. It creates a coherent history; it is not the future optimiser and is not a claimed commercial benchmark.

Version v2 corrects temporal leaks, stock continuation and accounting gaps found in review. For pre-decision inputs, use `snapshot(path, "2025-07-04", phase="before_ordering")` or add `--phase before_ordering` to the export command. Raw PO status is immutable placement state; snapshot status is computed at its cutoff. Invalid/out-of-period reads are rejected and never create SQLite files. Empty CSVs retain headers, and exports always include the synthetic warning.

Rebuild v1 artifacts rather than mixing them with v2. See `docs/DISTRIBUTOR_DATA_REVIEW.md` for the review findings and `docs/DISTRIBUTOR_DEMO_DATA.md` for the current data dictionary.
