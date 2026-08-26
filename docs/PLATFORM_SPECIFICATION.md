Possible Prototype — Retail Optimization Platform

1. Core Idea

Build one consolidated retail / inventory optimization platform, rather than three disconnected applications.

The platform should demonstrate how a small or medium-sized company can take messy operational sales and inventory data and turn it into concrete decisions that:

* Reduce unnecessary inventory
* Reduce working capital tied up in stock
* Reduce stockout risk
* Allocate stock more efficiently
* Avoid unnecessary markdown/clearance losses
* Improve overall margins

The prototype is not intended to pretend that we already have a universal SaaS product.

Instead, it is a working demonstration of the type of optimization system we could adapt to a client’s own operational data and constraints.

⸻

2. Dataset Available

The initial prototype uses an anonymized real-world retail dataset containing approximately:

* 125,751 sales records
* 284,755 inventory-state records
* 2,326 products
* 40 stores
* 30 suppliers
* Approximately 11 months of history
* Sales and returns
* Promotions and markdowns
* Historical inventory levels
* Selling prices
* Product costs / COGS
* Product hierarchy
* Supplier information

The data also contains realistic operational complications:

* Intermittent demand
* Returns
* Negative inventory records
* Promotions
* Markdown stages
* Changing inventory costs
* Stock tracking gaps
* Slow-moving inventory
* Different demand patterns across stores

This makes it useful for demonstrating how an optimization system deals with messy real-world operational data rather than a perfectly clean synthetic dataset.

⸻

3. Proposed Platform

Instead of building three independent applications, build one optimization platform containing several modules.

Platform Modules

1. Smart Inventory Optimizer

Question:

How much inventory should we hold, and when should we replenish it?

2. Store Allocation Optimizer

Question:

Given limited inventory, where should those units be allocated?

3. Markdown Optimizer

Question:

When should slow-moving inventory be discounted, and by how much?

These modules share the same underlying:

* Sales data
* Inventory data
* Demand forecasting
* Product information
* Financial calculations
* Store information

Therefore they naturally fit together as one platform rather than three unrelated demos.

⸻

4. Module 1 — Smart Inventory Optimizer

Business Problem

Companies frequently hold too much inventory in some products while carrying too little inventory in others.

Excess inventory:

* Ties up working capital
* Creates storage costs
* Increases markdown risk
* Can eventually result in clearance below cost

Insufficient inventory:

* Creates stockouts
* Risks lost sales
* Reduces service levels

The optimizer should answer:

How much inventory should this store/product hold, and when should it replenish?

⸻

Historical Analysis

For a selected:

Store → Product / Product Category

the application could show:

* Historical sales
* Historical inventory
* Sales velocity
* Promotions
* Returns
* Selling price
* Product cost
* Gross margin
* Inventory value
* Slow-moving periods

⸻

Demand Forecasting

The system estimates expected future demand.

Because the dataset contains extremely intermittent demand at individual SKU-store-day level (over 98% of series exhibit intermittent sparsity under Syntetos-Boylan criteria), we apply appropriate forecasting methodologies rather than naive daily regressions:

* **Hierarchical & Aggregated Forecasting:** Forecast demand at the weekly `Subcategory x Store` or `Segment x Store` level and disaggregate to individual SKUs based on historical share.
* **Intermittent Demand Models:** Apply Croston, TSB (Teunter-Syntetos-Babai), or zero-inflated ML models (e.g. LightGBM with Tweedie / Poisson loss).
* **Censored Demand Adjustment:** Correct historical sales for stockout periods (when on-hand inventory was zero) so unconstrained consumer demand is not artificially underestimated.

The eventual website does not need to overwhelm the client with these technical details.

The model exists to support the business decision.

⸻

Optimization Inputs

Some information is observed directly:

* Sales
* Inventory
* Selling price
* Cost
* Store
* Product
* Promotions
* Returns

Other variables are not available in the public dataset.

For the demonstration, these should become explicit user-configurable assumptions, for example:

Supplier Lead Time:       10 days
Target Service Level:     95%
Annual Holding Cost:      20%
Reorder Cost:             €50
Minimum Order Quantity:   5 units

These assumptions must always be clearly labelled as simulated parameters.

When working with an actual client, these assumptions would be replaced with their real operational values.

⸻

Inventory Recommendation

The system could calculate:

* Expected future demand
* Target inventory
* Safety stock
* Reorder point
* Suggested replenishment quantity
* Overstock risk
* Stockout risk
* Expected inventory value

Example:

PRODUCT: PROD-140871
STORE: STR-1235
Current Inventory:          17 units
Expected 4-week Demand:     8 units
Recommended Target Stock:   11 units
Reorder Point:              4 units
Safety Stock:               3 units
Current Inventory Value:    €860
Recommended Inventory:      €557
Potential Capital Release:  €303

⸻

5. The Killer Feature — Historical Simulation

This is probably the most important part of the entire prototype.

Instead of simply saying:

“Our model predicts demand.”

we simulate what would have happened historically if the optimized inventory strategy had been used.

**Simulation Integrity & Anti-Leakage Guardrails:**
* The simulation engine operates in a strict daily walk-forward loop (from date $t_0$ to $t_{\text{end}}$).
* It conditions decisions strictly on information available on or before day $t$.
* It intentionally ignores the retrospective `End Date` column in the raw inventory ledger (which records future transition timing) to prevent any lookahead bias.
* Demand during stockouts is treated as lost sales (or unfulfilled demand) rather than zero customer appetite.

The system compares:

Observed Historical Strategy

vs.

Simulated Optimized Strategy

Potential metrics:

Metric	Historical	Optimized
Average Inventory	X	X
Inventory Value	€X	€X
Inventory Turnover	X	X
Estimated Service Level	X%	X%
Estimated Holding Cost	€X	€X
Stockout Risk	X%	X%

The final result should translate into something immediately understandable:

18% less average inventory capital required while maintaining a simulated 95% service level.

Or:

€184,000 less working capital tied up in inventory under the optimized policy.

Any such result must clearly state that it comes from a historical simulation under specified assumptions, rather than claiming that money was actually saved by a real client.

⸻

6. Module 2 — Store Allocation Optimizer

Business Problem

The same product can perform very differently across different stores.

One store may have:

15 units sitting on the shelf with almost no demand.

Another store may have:

2 units remaining with strong expected demand.

This creates another optimization problem:

Given limited available inventory, where should each unit go?

⸻

Example

Suppose the company receives:

100 units of Product X

and needs to allocate them across 40 stores.

Instead of simply dividing them equally, the optimizer considers:

* Expected demand
* Existing inventory
* Historical sales velocity
* Product margin
* Store performance
* Stockout risk

The optimizer might recommend:

STR-1006    12 units
STR-1010     4 units
STR-1044     9 units
STR-1075     2 units
STR-1105     0 units
...
--------------------
TOTAL       100 units

subject to the constraint:

Total allocated inventory ≤ Available inventory

Additional business constraints could later be added.

⸻

Why This Is Valuable

This is a genuine constrained optimization problem.

It demonstrates that the platform doesn’t just predict something.

It actually recommends:

Where should the company put its limited resources?

This also connects nicely to Max’s original idea of demonstrating mathematical/constrained optimization.

⸻

7. Module 3 — Markdown Optimizer

Business Problem

Slow-moving inventory creates a difficult trade-off.

Discount too early

The company sacrifices margin unnecessarily.

Discount too late

The company:

* Holds dead inventory for months
* Ties up capital
* Eventually may have to liquidate it at an enormous discount

Our dataset is particularly interesting here because it contains:

* Full Price
* Promo
* Markdown Tier 1
* Markdown Tier 2
* Clearance

The initial audit found dramatically different realized margins between these regimes.

Approximately:

Full Price          +48% margin
Promo               +27%
Markdown Tier 1      +7%
Markdown Tier 2     -13%
Clearance           -79%

This creates a very interesting optimization question:

When should we discount inventory before it becomes economically expensive to continue holding it?

⸻

Potential Inputs

The model could consider:

* Current inventory
* Inventory age
* Historical sales velocity
* Expected future demand
* Selling price
* Product cost
* Historical promotion response
* Current margin
* Holding cost
* Probability of eventual clearance

⸻

Possible Recommendations

Healthy

Continue selling at full price.

Slow Moving

Demand has weakened, but discounting is not yet economically justified.

Markdown Candidate

Moderate markdown recommended.

Clearance Risk

High probability of future liquidation. Earlier markdown may preserve more margin.

⸻

Optimization Objective

The objective should NOT simply be:

Sell as many units as possible.

Instead, optimize something closer to:

Expected future gross margin − inventory carrying cost − expected clearance loss

This turns the feature into genuine decision support rather than a basic pricing model.

⸻

8. How Everything Fits Together

Eventually the platform could operate approximately like this:

             RAW COMPANY DATA
                    |
                    v
        Sales + Inventory Analysis
                    |
                    v
             Demand Engine
                    |
          +---------+---------+
          |                   |
          v                   v
 Inventory Planning      Markdown Analysis
          |
          v
   Store Allocation
          |
          v
     Optimization
          |
          v
 Historical Simulation
          |
          v
      € BUSINESS IMPACT

For example:

Step 1

Forecast demand for Product X.

Step 2

Determine how much total inventory is required.

Step 3

Determine where that inventory should be allocated.

Step 4

Continuously identify inventory becoming slow-moving.

Step 5

Recommend markdowns where holding inventory is becoming economically worse than discounting it.

Step 6

Show the expected financial effect of these decisions.

⸻

9. Recommended Development Strategy

Build ONE Platform, But Incrementally

Do not attempt to implement everything simultaneously.

Phase 1 — Smart Inventory Optimizer

Build the complete:

Data → Forecast → Optimization → Simulation → Financial Impact

pipeline.

This becomes the flagship website demo.

⸻

Phase 2 — Store Allocation Optimizer

Reuse the demand engine from Phase 1.

Add constrained optimization across stores.

This demonstrates stronger operations-research capabilities.

⸻

Phase 3 — Markdown Optimizer

Reuse:

* Demand forecasts
* Inventory history
* Product age
* Margin calculations

and add markdown decision support.

⸻

At that point we have one coherent:

Retail Optimization Platform

with three connected capabilities:

Inventory
Allocation
Markdown

rather than three random ML demos.

⸻

10. How We Should Position This to Clients

We should NOT initially market this as:

“We have built a universal inventory SaaS product.”

That would be misleading and unnecessarily restrictive.

Instead:

We build data-driven optimization systems around a company’s existing operational data and business constraints. This platform demonstrates the types of inventory, allocation and pricing decisions such systems can optimize.

This is important because every real company will have different:

* Supplier lead times
* Purchase-order processes
* Minimum order quantities
* Storage capacities
* Supplier constraints
* Holding costs
* Transportation costs
* Service-level requirements
* Expiry/shelf-life requirements
* Business rules

For an actual client, their data replaces the assumptions used in the public demonstration.

⸻

11. Website / Demo Experience

The eventual public website should not feel like a Jupyter notebook.

A potential client should be able to open the demo and immediately understand what is happening.

Possible experience:

Choose Store
      ↓
Choose Product / Category
      ↓
See Historical Business Situation
      ↓
Run Optimization
      ↓
See Recommendation
      ↓
Compare Historical vs Optimized
      ↓
See Estimated € Impact

Technical details such as:

* Forecasting methodology
* Optimization formulation
* Constraints
* Backtesting methodology

can exist under something like:

How it works

for technically interested visitors.

But the primary interface should focus on business decisions and financial impact.

⸻

12. Core Principle

The prototype should not primarily attempt to impress people by saying:

“We used Croston + LightGBM + MILP + stochastic optimization.”

The person running the company may not care.

Every important screen should instead answer:

What problem did we identify?

What decision do we recommend?

Why?

What is the expected financial impact?

The forecasting models, mathematics and optimization algorithms are what allow us to produce that answer.

They are the engine, not the product.