# Storage cleanup — 18 September 2026

## Outcome

Approximately **764 MiB** of local project storage was removed after the distributor optimiser was stopped and the Supplier Basket Review direction was agreed.

## Removed

- `.venv/` — 447 MB; reproducible from `requirements.txt`.
- `data/raw/` — 133 MB; the two historical retail CSVs are tracked in Git and recoverable from commit `b2bde6a`.
- `artifacts/part1-final/` — 133 MB of old replay tables.
- Old dataset-search, feasibility, distributor-generation, development-batch, reserved-evaluation, diagnosis and trial-01 artifacts — approximately 44 MB.
- Unused website design-reference screenshots — 7.5 MB.
- Pytest caches, Python bytecode and macOS metadata files.
- The four large trial-02 case reports and two one-off tracing scripts after their conclusions were reduced to compact retained evidence.

## Retained

- Git history and all current source and test code.
- Repository rules, requirements and small decision-history documents.
- The authoritative new direction: `docs/SUPPLIER_BASKET_SHOWCASE_BRIEF.md`.
- The final negative research report: `docs/DISTRIBUTOR_ADAPTIVE_DISCRETE_TRIAL_02.md`.
- Compact trial-02 evidence only:
  - `contract.json`
  - `summary.json`
  - `regression-trace.json`
  - `regression-isolation.json`
  - `source.tar.gz`

The retained artifact directory is approximately **92 KB**. The whole working copy is now roughly **40 MB including the 37 MB Git database**.

## Recovery and verification boundary

- The deleted tracked retail CSVs can be restored from Git if historical work is ever needed.
- The deleted generated artifacts and design screenshots were untracked and were removed permanently.
- The active suite passed **167 tests immediately before cleanup**.
- Tests were not rerun after cleanup because the 447 MB virtual environment was intentionally removed. Recreate it from `requirements.txt` when implementation begins.

This cleanup did not delete source, tests, Git history or the compact evidence needed to explain why the former optimiser direction was stopped.
