# Estimated demand

`src.demand.asof` estimates demand one day at a time. Recorded purchases remain observed facts. On an empty or depleted shelf, the estimator uses rates learned through the previous day and records the fallback and information cutoff.

Only known positive-stock days enter a rate denominator. Bridged stock days are marked as estimated exposure. Unknown stock is not silently treated as an empty shelf.

The output is called `estimated_demand`. It is not verified “true demand”, and estimated missed customers are not treated as observed purchases in replay.

Build it through the shared runner:

```text
python -m src.build_part1 --output-dir PATH
```
