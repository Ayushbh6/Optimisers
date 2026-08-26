# Business Context & Retail Domain Overview

## 🏬 What Business Is This?

This dataset comes from a real-world, anonymized **mid-market specialty retail chain** specializing in footwear and youth apparel (comparable to brands like *Clarks*, *Skechers*, *DSW*, or *Schuh*).

```
========================================================================================
ENTERPRISE OVERVIEW
========================================================================================
Business Model          Brick-and-mortar specialty footwear and apparel retail
Store Network           40 physical storefronts (STR-1006 through STR-1369)
Sales Channel           Physical storefronts ("Channel Alpha")
Catalog Breadth         2,326 distinct SKUs (products)
Supplier Network        30 manufacturing vendors (Vendor 0010 through Vendor 0262)
Observation Period      11 consecutive months (June 1, 2025 – April 24, 2026 / 328 days)
Total Revenue           $10.48 Million
Total COGS              $5.85 Million
Gross Profit Margin     $4.63 Million (44.21%)
Average Standing Stock  $2.40 Million tied up in inventory (at cost value)
Days Sales of Inventory 134.9 days (Inventory turnover: 2.71x per year)
========================================================================================
```

---

## 👟 Product Catalog Breakdown

The company's product hierarchy spans **3 Divisions**, **27 Categories**, **51 Subcategories**, and **600 Segments**:

```
                                  ENTERPRISE REVENUE ($10.48M)
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
      Scholar Footwear                  Femme Footwear                  Junior Apparel
      $7.34M (70.0% of Sales)           $2.71M (25.9% of Sales)         $431.7K (4.1% of Sales)
      72,771 units sold                 25,876 units sold               18,348 units sold
      881 active SKUs                   714 active SKUs                 731 active SKUs
      Margin: 46.1%                     Margin: 39.6%                   Margin: 41.0%
      ──────────────────────            ──────────────────────          ──────────────────────
      • Trailblazer Everyday            • Trailblazer Casual            • Crew & Graphic Tees
      • Modern & Retro Legend           • Court Classics                • Cozy Pullovers & Hoodies
      • Court Casuals                   • Fashion & Winter Boots        • Cozy Trousers & Pants
      • Canvas Styles (Drifter)         • Sandals & Wedges              • Denim & Gift Bundles
```

---

## 📄 The Two Operational Data Files Explained

### 1. The Sales Ledger (`retail_sales_ml_apl.csv` — 125,751 rows)
The cash register (POS) log capturing daily customer purchasing and return behavior across all 40 stores:
* **Transaction Details:** Date, Store, Product SKU, and Quantity Sold.
* **Pricing & COGS:** Realized retail price paid by the customer vs. wholesale unit cost (COGS) paid to the vendor.
* **Discount Regimes:** Tracks whether an item was sold at regular Full Price ($48.3\%$ margin), Promotional discount ($26.7\%$ margin), Markdown Tier 1 ($7.2\%$ margin), Markdown Tier 2 ($-13.0\%$ loss), or Clearance liquidation ($-78.6\%$ loss).
* **Customer Returns:** $5.96\%$ of all recorded sales transactions are customer returns, which return directly back to shelf inventory.

### 2. The Inventory Ledger (`retail_inventory_ml_apl.csv` — 284,755 rows)
The stockroom ledger tracking physical on-hand inventory levels and stock valuations over time:
* **Time-Window Intervals (SCD Type 2):** Each row represents a date range `[Start Date, End Date]` during which a store held an exact count of units on the shelf.
* **Inventory Value:** Tracks unit cost, unit selling price, total stock cost value, and total stock retail value on any given day.
* **Inventory Depletions & Inbounds:** Captures the real-world step-downs from sales and step-ups from vendor shipments.

---

## 🎯 The Core Business Problems Our Platform Solves

This business is profitable, but suffers from two classic retail supply-chain inefficiencies:

1. **Slow-Moving Inventory & Trapped Working Capital:**
   * On any given day, **$\$2.4\text{ Million}$ of cash is locked up as inventory** on store shelves.
   * It takes an average of **135 days** to turn inventory over ($2.71\times$ per year).
   * Certain slow-moving items sit in stockrooms for over **200 days** before selling a single pair.

2. **Severe Margin Collapse on Late Markdowns:**
   * When items fail to sell at full price, the company waits too long and is forced into deep markdowns.
   * In Markdown Tier 2 and Clearance, the company loses money on every item sold (selling at **$11.61** what cost **$20.74** to procure).
   * Over the 11-month period, liquidation markdowns destroyed over **$\$23,700$** in net profit.

3. **Uneven Multi-Store Allocation:**
   * Sales velocity varies widely across the 40 stores (the top store generates **$3.5\times$ more revenue** than the lowest store).
   * Without intelligent allocation, fast-selling stores experience stockouts while slow-selling stores hold idle safety stock.

---

## 🛡️ Anonymization Notice
To protect commercial privacy in the published dataset:
* Store names are encoded as `STR-1006` through `STR-1369`.
* Supplier names are encoded as `Vendor 0010` through `Vendor 0262`.
* Product IDs are encoded as `PROD-100043` through `PROD-170517`.
* Category taxonomies, calendar dates, units, prices, and costs reflect genuine enterprise commercial activity.
