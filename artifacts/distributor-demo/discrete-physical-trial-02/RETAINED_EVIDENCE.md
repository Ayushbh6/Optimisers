# Retained compact evidence

The large generated databases, four detailed case reports and one-off tracing scripts were removed during the 18 September 2026 storage cleanup. The following compact files remain:

| File | SHA-256 |
|---|---|
| `contract.json` | `2f68a9e50433494bec7d8a14bbf8f0aa240a661d87697b3bd120f2b364c810e3` |
| `summary.json` | `2927f6a79d696052bc6d7193800f46e4a1ab760cc3dc30b446df3520ebae9e04` |
| `regression-trace.json` | `60b46ec5f961da7988911c4affce2d0ccb2724cf020123af11cc60c0e09903e6` |
| `regression-isolation.json` | `afab2cc81da63a0db2e2ad4c45dc28de3c8dce0b1fedc158a812237d9018bcb5` |
| `source.tar.gz` | `4e9ba7619eb659d295655daf1a400dd493d7fc551302b60d470874a6978ae21d` |

The two regression JSON files contain historical hashes for the deleted detailed ample-stock case and tracing scripts. Those deleted files cannot be independently rechecked from this lean copy. The frozen numerical implementation itself remains in `source.tar.gz`, while the aggregate outcome and exact affected order-line facts remain in the retained JSON and repository report.

This is sufficient to explain the stopped direction, but it is intentionally not a complete rerunnable evaluation bundle.
