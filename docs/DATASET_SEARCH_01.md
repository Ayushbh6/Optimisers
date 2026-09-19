# First dataset search: delivery route planning

> **Superseded for demo priority, 13 September 2026:** the user clarified the actual prospective clients. See [TARGET_CLIENTS.md](TARGET_CLIENTS.md). Delivery routing is parked as a possible demo 3/4, not selected for either of the first two demos. The technical findings below remain a record, not the current project direction.

13 September 2026. Recommendation: take **Delivering Data** into a bounded feasibility review. It is a promising dataset, not a proven successful demo. No routing policy has been implemented or tested.

The user has accepted moving on from the retail dataset as the proposed flagship. The aim remains 2–3 credible website demos; this search selects one candidate first.

## Candidate and provenance

[Delivering Data: A Real-World Dataset for Last-Mile Delivery Optimization](https://zenodo.org/records/15672291), by Anna Vrani, Savvas D. Apostolidis, Athanasios Ch. Kapoutsis and Elias B. Kosmatopoulos. Pin DOI `10.5281/zenodo.15672291`, published 16 June 2025, rather than the earlier version.

The source describes pharmaceutical deliveries by a logistics company around Athens. Orders are recorded business requests; road travel estimates come from Google, and service durations/windows reflect recipient categories and company guidelines. They are not observed delivery outcomes. Exact customer coordinates are withheld. [Source paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12206052/), [author repository](https://github.com/annavrani/Delivering-Data).

The [dataset metadata](https://zenodo.org/api/records/15672291) specifies **CC BY 4.0**, allowing commercial reuse with attribution. The article has a separate noncommercial licence: do not treat its figures or the author's unlicensed code as covered by the data licence.

## What I actually checked

Downloaded the 2,926,700-byte source archive into memory, verified its published checksum, and inspected all order sheets and all 36 matrix workbooks. Retained only orders and the four day-one matrices, plus an inspection script and evidence JSON: about **227 KB** in total.

- **653 requests across nine days**, with 63–84 requests per day.
- Recorded shipment weight and volume; supplied service duration and delivery window.
- Every day has distance and three traffic-time matrices.
- All matrices are square, complete and nonnegative. Their identifiers exactly match that day's orders plus node 0.
- Each day's order identifiers are unique; weights/volumes are positive; no reversed time windows.
- Day-one matrices have zero diagonals and positive travel values between distinct nodes.
- Day one contains **469 directed pairs** where the most-likely value is outside the optimistic–pessimistic interval. Do not sort or silently repair them. Google explicitly says its best-guess prediction can fall outside that interval because it incorporates live traffic. These are alternative estimates, not statistical confidence bounds. [Google explanation](https://developers.google.com/maps/documentation/routes/traffic-model).

Reproduction: `python3 -B artifacts/dataset-search/delivering-data/inspect_source.py`. The script verifies the archive and all-day structural checks; the additional day-one diagonal and traffic-order checks were performed separately during review.

## Why a buyer would care

A dispatcher must assign orders to vehicles and choose delivery order. Less driving can free driver time and vehicle capacity, provided loads fit and deliveries meet their windows. Those are concrete operating decisions.

Capacity and delivery-window constraints are established routing practice, supported by [Google's commercial route optimisation API](https://developers.google.com/maps/documentation/route-optimization/parameter-list) and [open-source OR-Tools](https://developers.google.com/optimization/routing/vrptw). A credible demo would show valid schedules, load checks, exceptions and transparent comparisons. Merely displaying a solver result would not distinguish us.

| Gate | Assessment |
|---|---|
| Honest | Conditional pass: real orders, but modelled travel/service inputs and a declared fleet scenario. No historical savings claim. |
| Valuable | Pass for the decision: dispatcher workload, driving distance and delivery feasibility matter. Improvement is still untested. |
| Real-world standard | Pass for problem fit: constrained delivery planning is established practice. This does not establish production readiness. |
| Sellable | Conditional: could demonstrate practical planning skill if comparisons are fair and improvements survive all-day testing. |

## The limits we must accept

Actual fleet count/capacity, historical routes, actual arrival times, driver shifts and operating costs are absent from the inspected archive. Node 0 appears to be the depot, but this remains an inference requiring source confirmation or explicit scenario labelling. Orders must be treated as available before dispatch; their actual booking times are not supplied.

We cannot claim to beat the company's original routes, prove cash savings, predict measured on-time performance, or represent pharmaceutical compliance. Nine days also cannot establish performance across seasons. Without coordinates, a route schedule or anonymous network is honest; an invented geographic map is not.

These gaps do **not** mean asking the user for inaccessible company records. We either accept a clearly labelled planning scenario or reject this dataset if that is insufficient for the intended demo.

## Proposed next step, pending decision

First confirm depot/time-window meanings from public source material and define the demo's exact claim. Fix fleet capacities, shifts, depot rules and comparison methods before solving anything; justify them independently of desired results. Reject the candidate if those assumptions dominate the story.

If accepted, a later bounded experiment would compare valid plans for all nine days using identical orders, fleet and time rules. Use a competent construction method with local improvement and a recognised solver reference; disclose computing budgets. Do not compare only against random routes. Keep separate development and evaluation days and report every day, including failures.

Potential claim: **“On these published delivery orders, under the stated fleet and travel assumptions, our planner reduced planned driving against the named baseline while serving every order within the supplied constraints.”** No percentage is promised. Success criteria and runtime limits must be agreed before the experiment, not chosen after seeing results.

## Other candidates screened

- [FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K): stronger candidate for a separate forecasting demo; stockout information helps, but normalized sales and missing physical stock/order inputs do not automatically establish inventory savings.
- [ORTEC EURO NeurIPS routing data](https://github.com/ortec/euro-neurips-vrp-2022-quickstart/blob/main/LICENSE): relevant real routing data, but the instance licence is noncommercial; not selected for a client-acquisition website under its published terms.

**Verdict: proceed with the bounded fit review of Delivering Data. Do not commit to building the demo yet.** It connects recorded requests to a direct planning decision more cleanly than the previous retail data connects recorded sales to hypothetical inventory savings.

## Resumed review: dataset selection verdict

Further source review and read-only calculations completed on 13 September. **Select this as the first dataset candidate for a bounded experiment, subject to accepting the explicitly modelled fleet.** The public article and author's example code do not resolve node 0's depot meaning or supply fleet capacities. This is an unresolved source limitation, not a request for private records.

The article defines the windows as earliest/latest **arrival** times relative to 08:00. A proposed model should apply those bounds to arrival/service start, rather than silently requiring service completion before the deadline. Service durations must still consume driver time. Departure at 08:00, returning to node 0, no split deliveries and the route-end limit would be declared scenario rules, not reconstructed historical facts. [Article text, accessible XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12206052/fullTextXML).

Additional calculations from all nine retained order sheets:

| Daily workload | Minimum | Maximum |
|---|---:|---:|
| Recorded shipment weight | 687.63 kg | 1,880.50 kg |
| Recorded shipment volume | 3.213 cubic metres | 9.020 cubic metres |
| Supplied service time, summed across stops | 6.40 hours | 9.60 hours |

Individual requests reach 453.153 kg and 1.95178 cubic metres (different requests). Those values help detect unsuitable vehicle assumptions; they do not establish which vehicles the operator used. All windows start at 08:00 and end at 11:00, 13:00 or 14:00. Thus this is a morning delivery-planning problem with category-based deadlines, not a rich appointment-booking dataset.

There is enough work to justify investigating vehicle assignment and stop ordering, but workload alone does not prove room for improvement. A dispatcher-facing product could show order assignment, arrival schedules, load use, driving totals and explicit reasons when an order cannot fit. This matches the decisions described in [Google's commercial routing documentation](https://developers.google.com/maps/documentation/route-optimization/overview). Established open-source tools such as [PyVRP](https://pyvrp.org/setup/why_pyvrp.html) already support the core constraints. Using one honestly is acceptable; portraying its algorithm as our invention is not.

### Proposed experiment acceptance criteria

These are proposed project thresholds, not established industry requirements, and must be fixed before running policies:

1. Use days 1–3 for development and days 4–9 for evaluation. All days have been inspected for data fitness, so do not call the evaluation data unseen; no policy results have been viewed.
2. Fix a small set of fleet scenarios and the runtime budget before solving. Evaluate the full set, without selecting the one producing the best headline. Capacity must cover both weight and volume; no orders may be discarded.
3. Require independently checked, complete, constraint-valid plans on every evaluation day in the nominated primary scenario. Solver timeout or failure must not be called proof that the problem is impossible.
4. For a driving-reduction headline, propose at least **10% less total planned distance** across the six evaluation days against a disclosed competent baseline, with improvement on at least five days and no day more than 5% worse. Vehicle availability, permitted working time and objectives must match. Report vehicle use and total driver time alongside distance so hidden trade-offs remain visible.
5. Compare against a recognised solver using the same constraints. If the result is ordinary solver performance, sell the quality of the planning application and integration, not superior algorithmic performance. A thin solver wrapper alone is insufficient for the intended showcase.
6. Propose a **60-second planning budget per day** on a disclosed machine, with repeated runs where randomness applies. Validate returned schedules separately. Evaluate the fixed schedules against each supplied traffic matrix; report late arrivals, without interpreting scenarios as probabilities.

Reject the savings-led demo if improvement depends on a weak baseline, favourable fleet choices, dropped orders or relaxed deadlines. Reject this dataset altogether if the team wants a verified historical savings case or a geographically accurate route-map demo: neither is supported by these files. No routing experiment or application implementation has started.
