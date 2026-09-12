# Dated reorder policy

`src.policy.asof` turns an as-of forecast into the existing reorder recommendation. It uses the latest valid cost for the same product-store pair known at the decision date. Missing or invalid cost makes the recommendation unavailable; no made-up cost is used.

The current Part 1 settings remain explicit: ten-day lead time, 95% nominal target, 20% annual holding rate, minimum order quantity five and the existing stocking threshold. Better economic stocking rules belong to Part 2.

Build it through the shared runner:

```text
python -m src.build_part1 --output-dir PATH
```
