# Phase 1 — Data-issue contract

| Messy record | Business cause | Required treatment |
|---|---|---|
| Product aliases such as `Oat Crkr` | Different warehouse and product-master labels | Normalize automatically and retain the source row. |
| Oat quantity `5` with blank UOM | Warehouse export dropped the unit | Block until the buyer confirms five 12-unit cases = 60 units. |
| Five-case purchase followed by four-case amendment | Buyer changed the supplier line | Keep both rows; use the open amendment. |
| Customer shelf-life rule | Customer contract differs from stock expiry | Preserve as a hard dispatch constraint. |
| Dated supplier change cut-off | Supplier accepts edits only until a stated date | Reject changes after the cut-off. |

No decorative errors or result labels are permitted in the raw files.
