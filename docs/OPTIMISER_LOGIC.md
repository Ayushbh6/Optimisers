# Optimiser Logic — Plain-Language Notes

> Status: Working notes. Written to be understood without math jargon.
> Purpose: Track the whole flow and the shared understanding of the optimiser, in simple language.
> This is the "what are we actually doing and why" document. The technical details live elsewhere.

---

## 1. What we have

**Two files of raw data.**

### File A — The Sales Log (125,751 rows)
Every time something got sold in a store, there's a line.

Each line = one product, in one store, on one day, at one price type.

"Price type" means:
- Full price
- Promo
- Markdown (3 levels, down to Clearance)

Also has returns (~6% of rows = customers bringing stuff back).

### File B — The Inventory Log (284,755 rows)
This is NOT "here's how much we had every day."

It's "here's a stretch of days where the shelf count stayed the same, from date X to date Y."

When the count changes (someone buys, or a shipment arrives), a new stretch begins.

So the full history of "how many units did store 1044 have of product 12345" is a list of these date-window records.

### The business in one sentence
A 40-store shoe + kids-clothes chain. 2,326 products. 11 months of data. ~$10.5M revenue.
Profitable (44% margin), but sitting on ~$2.4M of stock that takes ~135 days to sell through.
When things don't sell, they eventually get liquidated at a big loss.

---

## 2. What a real solution in 2026 produces

Not a "prediction." A **decision + a receipt.**

A real modern inventory system answers three questions:

1. **How much should I hold?**
   → "For product X in store Y, keep about 11 units. Reorder when you hit 4."

2. **Where should I send the stock?**
   → "We have 100 units. Don't split evenly — store A gets 12, store Z gets 0."

3. **When should I cut the price?**
   → "This item's been sitting 90 days. Cut 30% now, before you're forced to clear it at −79%."

And the part that actually convinces a business person (the "receipt"):

> "We replayed your own last 11 months through our rules, and you would have held ~18% less cash in inventory while selling at the same rate."

That last sentence is the sales pitch. The models are just how you *get* that sentence honestly.

### What "18% less" means (precisely)
If the company had followed our reorder rules last year instead of whatever they actually did,
they would have held ~18% less cash tied up in inventory — while still selling the same amount.

"Less cash in reserve" = fewer units on shelves = less working capital frozen.

Why "while selling at the same rate" matters: it's the difference between
- cutting stock smartly (hold less of the slow stuff, keep enough of the fast stuff), vs
- just starving the shelves (which kills sales).

The claim only has value if sales don't drop.

> Honest note: the "18%" number is currently an *example* from the docs, not real yet.
> The whole job is to make a number like this true and defensible through simulation.

---

## 3. What the scary words actually mean

| Jargon | What it really means |
|---|---|
| Intermittent demand | Most products barely sell. The typical product-store combo sells ~3 times in 11 months. Most days are "sold 0." |
| Croston / TSB | Old-school methods for rare sales: separately guess *how often* it sells and *how many* when it does. |
| LightGBM + Tweedie loss | Modern ML to guess future sales, tuned for data that's mostly zeros. Optional, not where we start. |
| Censored demand / lost sales | If the shelf was empty for 2 weeks, we don't know how many would have bought. We only see "0 sold," which under-counts true demand. |
| Walk-forward simulation / backtest | Replay the calendar day by day, only using info known *on that day*, and see how our rules would have performed. Like a trading backtest, but for shelves. |
| Lookahead bias / leakage | Accidentally letting the model "cheat" by peeking at the future. Must be avoided. |
| Safety stock | Extra buffer so a small demand surprise doesn't empty the shelf. |
| (s, S) policy | A simple rule: "when stock drops to `s`, order up to `S`." That's it. |
| Knapsack / MILP | "We have a limited pile of units and 40 stores that want different amounts — find the split that earns the most." |
| Hierarchical pooling | A single product-store has almost no data, so let it borrow signal from its whole category across all stores. This is the actual trick that makes this work. |
| ADI | Average number of days between sales. ~97 days = "sells about once a quarter." |

---

## 4. Where the "$2.4M / 135 days" number came from

Not calculated by hand — it's printed in the docs and the audit.

- **Average standing stock = $2,404,541.94 (~$2.4M).**
  = every day, sum up "how much did all the stock on shelves cost," then average across the year.
- **135 days to sell through = Days Sales of Inventory.**

```
$2.4M sitting in stock  ÷  ~$6.5M stock cost per year  →  ~0.37 years  →  ~135 days
```

So "sitting on $2.4M that takes 135 days to turn over"
= the company's cash is trapped in shelves for ~4.5 months before it comes back as sales.

---

## 5. Our constraints (the honest limits)

1. **We can't forecast from almost no data.**
   A product that sold 3 times has no "pattern" to learn. Individual predictions are nearly useless — we must lean on category/group patterns. This is the #1 technical reality.

2. **The inventory data needs reconstruction.**
   We have date-window records, not daily counts. ~26% of sales don't line up with any inventory record.
   Turning this into a clean "how many units were on the shelf each day" table is real work — and where projects like this quietly die. Do it first.

3. **We can't see true demand during stockouts.**
   We have to estimate it. That estimate can make our backtest flatter itself if we're not careful.

4. **One year = no real seasonality.**
   We see one Christmas, one back-to-school. Can't claim a pattern from one data point.

5. **Some numbers are pure guesses.**
   Lead times, holding cost %, reorder cost — not in the data. We assume them, so we make them adjustable and clearly labelled.

---

## 6. The flow (5 steps)

```
START
  │
  ▼
Step 1: Rebuild "daily stock per product per store"
        (a clean table we can trust)
  │
  ▼
Step 2: Estimate "true demand" (fill the stockout gaps honestly)
  │
  ▼
Step 3: Forecast at the CATEGORY level, then split down to product
        (because individual products have too little data)
  │
  ▼
Step 4: Simple reorder rule: "when stock hits X, order up to Y"
  │
  ▼
Step 5: Replay last 11 months with our rules
        → "you'd have held €Z less cash, same sales"
  │
  ▼
SHOW THAT NUMBER
```

### The 5 steps in plain questions

| Step | Plain question | What it produces |
|---|---|---|
| 1. Rebuild | How many units were actually on the shelf each day? | A clean daily count per product. |
| 2. True demand | When the shelf was empty, how many sales did we miss? | A corrected "demand" number, not just "0". |
| 3. Forecast | How many will they want next month? | A number, forecast at category level, split down. |
| 4. Reorder rule | When do we restock, and how much? | "When stock hits 4, order up to 11." |
| 5. Replay & prove | If we'd used this rule last year, what happens? | "We'd have held €Z less cash, same sales." |

Everything else (markdown, allocation) plugs in *after* step 3, using the same demand numbers.

---

## 7. Step 1 details — where does the daily count come from?

**Mainly File B. But File A is the "truth-checker" that fixes B's gaps.**

- **B (inventory log)** gives the raw shelf counts over date windows. Primary source — it literally says "this store had 5 units from June 1 to June 12."
- **A (sales log)** tells us *why* the count changed, and lets us **fill the holes** in B.

Remember: ~26% of sales don't match any inventory window → B has gaps.
Those gaps are exactly where we use A to infer "there must have been stock here, because someone bought it."

```
B gives the skeleton (known counts over windows)
   +
A gives the heartbeat (when sales/replenishments happened)
   =
a clean, gap-free daily count table
```

Think of B as the frame of the house, A as the plumbing that tells you what flowed through on days the frame has holes.

---

## 8. Forecasting: category first, then split down

**Important correction to hold in mind:**
- 2,326 = actual unique products (SKUs).
- We forecast at the **category** level (a category sells enough times to have a real pattern).
- Then split the category's forecast **down to individual products** (using each product's historical share of category sales).

```
CATEGORY total demand  (enough data → reliable forecast)
        │
        ▼
split down to each PRODUCT (by its past share)
```

"Do one slice first" = pick **one category**, run the entire 5 steps for it, get one believable number.
Then widen to more categories.

No contradiction: the "slice" is a category, and forecasting already lives at the category level.

---

## 9. Is this a SaaS, or bespoke per client?

**Not a SaaS. It's a consulting/studio play.**

**Reusable (the ~30%):**
- Overall architecture (data → forecast → optimize → simulate → show money).
- The mathematical methods (intermittent forecasting, walk-forward simulation, allocation).
- The thinking and the playbook.

**Changes per client (the ~70%):**
- Their data looks different (columns, inventory format, hierarchy, industry).
- Their constraints differ (lead times, order minimums, shelf life, supplier rules).
- Their business rules differ (markdowns? returns? multiple warehouses?).

**So what are we actually selling?**
Not "a product that works on anyone's data."

We're selling:

> "We take a company's messy operational data and build them a decision system. Here's a worked example of how we think, on real data, with the result we produced."

The website's Project 01 is the **proof of capability** — a demonstration that we can do this hard thing.
Actual client work = get their data, remap the pipeline, rebuild the forecast to their specifics, hand them *their* number.

The optimizer is the flagship proof of skill, not a product we license.
It proves "we can turn messy data into money-decisions" — which is the service we actually sell.

---

## 10. What form does this take? (Separation of concerns)

There are **three different "things"** that must stay separate:

```
(1) THE ENGINE          →  the Python pipeline (data → forecast → optimize → simulate)
(2) THE DEMO            →  a nice interactive frontend running the engine on THIS dataset
(3) A CLIENT SYSTEM     →  bespoke, built per client on THEIR data
```

- **(1) is what we actually build.** It's code. Python. Modular, reusable.
- **(2) is how we *show* (1) to the world.** A clean web app, but running on our fixed, real dataset — not on uploaded files.
- **(3) is what we sell.** It never runs on our website. It's built fresh for each paying client.

### So is it a SaaS or "just scripts"?

**Neither extreme. It's (1) + (2).**

- **Not a SaaS** — no user accounts, no billing, no database of client data, no "upload your CSV" portal.
  That would pretend we have a universal product → fake maturity (which the website spec warns against).
- **Not just a pile of scripts** — a `print()` dump does not build credibility with a business owner.

**The right answer: a polished, interactive demo dashboard that runs our engine on this one dataset.**

### Why the demo needs a frontend

Think about who sees this: a business owner, ops manager, or CFO.

They don't want:
```
>>> print(results)
InventoryValue: 184000.0
```

They want:
> "Store STR-1044, product 'Court Casuals.' Here's your last 6 months. Here's what our rules recommend.
> Slide this 'service level' knob to 98% and watch the capital needed change. Here's the € impact."

A frontend doesn't make the math better — it makes the result **believable and legible**.
That's the whole game for credibility. The engine earns trust; the frontend *communicates* it.

### Why NOT an "upload your documents" portal

An upload portal says: "This is a general tool that works on anyone's data."

But it doesn't — every client's data is different (columns, inventory format, constraints).

If we built an upload portal, two bad things happen:
1. Someone uploads data, it breaks or gives garbage → we look incompetent.
2. We've promised universality we can't deliver → undercuts honest positioning.

Real client work is *bespoke*: we take their data, remap the pipeline, adapt constraints, hand them *their* system.
That happens in private, not through a website.

The website demo is a **worked example on our data**, not a self-serve tool.

### How this maps to what we build

```
                    ENGINE (Python, we build first)
                          │
                          ▼
              DEMO FRONTEND (we build second)
        runs the engine on THIS dataset only
        with interactive knobs (lead time, holding %, service level)
                          │
                          ▼
              THE WEBSITE embeds/links this demo
              as "Project 01" — proof of capability
```

**The order matters:** build the engine first, get one honest number, *then* wrap it in a frontend.
The frontend is just a display layer for the engine's output. No point skinning an engine that doesn't exist yet.

### Tech stack (honest & simple)

- **Engine:** Python (pandas / numpy / scipy, + a forecasting lib later).
- **Demo frontend:** a single-page app that calls the engine's output.
  No heavy backend or database needed — dataset is fixed, results pre-computed or computed on-demand.
- **No:** user auth, billing, multi-tenancy, client databases.

### The "one size fits all" reconciliation, in one line

> **The demo is not the product. The demo proves we can do the thing. The product is the bespoke system we build for each paying client — and that's where the ~70% custom work lives.**

The reusable ~30% (architecture, methods, playbook) travels from client to client.
The demo is just its most presentable proof.

---

## 11. Key principles to remember

1. **The model is the engine, not the product.** The product is the decision + the receipt (the € impact).
2. **Trust > cleverness.** When a client asks "why 8 units?", we need an answer we can say out loud, not "the model said so." → start simple.
3. **Be honest about assumptions.** Lead time, holding cost, service level are guesses → make them adjustable, labelled, and show the result is stable across them.
4. **One believable number on one slice > a half-built pipeline on everything.**
5. **Never let the model cheat (no peeking at the future).** The whole credibility rests on this.
