# Enterprise Retail Demand Forecasting & Inventory Optimization Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Phase%200%20Complete%20%7C%20Ready%20for%20Phase%201-success.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

A data-driven decision platform and operations-research engine for enterprise retail inventory management, multi-store stock allocation, dynamic markdown optimization, and walk-forward historical simulation.

---

## 🏗️ Repository Architecture

This repository is organized following clean Python and Data Science / Operations Research standards:

```text
.
├── README.md                      # Primary project orientation and architectural overview
├── .gitignore                     # Git tracking exclusions
│
├── audit/                         # Data Due Diligence & Technical Validation
│   ├── DATASET_AUDIT.md           # 12-Section comprehensive empirical audit report
│   ├── scripts/                   # Reproducible Python audit and validation scripts
│   │   ├── 01_basic_audit.py      # Column profiles, memory footprint, data types, nulls
│   │   ├── 02_grain_and_join_audit.py # Grain identification, keys, temporal interval join
│   │   ├── 02b_investigate_unmatched.py # Root-cause analysis for unmatched sales intervals
│   │   ├── 03_inventory_dynamics_and_reconciliation.py # Financial formulas & state deltas
│   │   ├── 04_case_study_reconstruction.py # End-to-end 5-SKU timeline reconstructions
│   │   ├── 05_demand_and_financial_deep_dive.py # Intermittency (Syntetos-Boylan), DSI, turnover
│   │   ├── 06_advanced_audit_and_leakage.py # Store spreads, promo elasticity, missing variables
│   │   └── 07_print_case_details.py # Formatted event logs for case studies
│   └── reports/                   # Audit data extracts and visual figures
│       ├── figures/               # High-res time-series plots & valuation charts
│       ├── advanced_audit.json    # Store summary, missing variables, leakage guardrails
│       ├── case_studies_data.json # Granular event logs for representative case studies
│       └── demand_financial_summary.json # High-level financial KPIs & demand classifications
│
├── docs/                          # System Architecture & Product Specifications
│   ├── BUSINESS_CONTEXT.md        # Plain-English company background, business model & retail domain
│   └── PLATFORM_SPECIFICATION.md  # Platform vision, module specifications & 3-phase roadmap
│
├── data/                          # Datasets (Tracked locally / Git LFS)
│   └── raw/                       # Raw immutable source data
│       ├── retail_inventory_ml_apl.csv # 284,755 rows: SCD Type 2 stock ledger
│       └── retail_sales_ml_apl.csv     # 125,751 rows: daily sales transaction slices
│
└── src/                           # Core Platform Source Code (Phased Development)
    ├── data/                      # Data loaders, cleaning, and SCD Type 2 interval processors
    ├── forecasting/               # Intermittent demand models (Croston, TSB, Tweedie LightGBM)
    ├── optimization/              # Stochastic (s, S) replenishment & MILP multi-store allocation
    └── simulation/                # Walk-forward backtester and counterfactual business simulator
```

---

## 🏬 The Business & Retail Domain

The dataset represents an **anonymized mid-market specialty retail chain** specializing in footwear and youth apparel (similar to *Clarks*, *Skechers*, or *DSW*):
* **Store Network:** 40 physical brick-and-mortar storefronts (`STR-1006` to `STR-1369`).
* **Catalog:** 2,326 SKUs from 30 manufacturing suppliers (`Vendor 0010` to `Vendor 0262`).
* **Core Revenue Drivers:** **Scholar Footwear** (70.0% of revenue), **Femme Footwear** (25.9%), and **Junior Apparel** (4.1%).
* **Commercial Baseline:** $10.48M annual revenue, 44.21% gross margin, with **$2.40M in average standing inventory capital** (134.9 Days Sales of Inventory).
* **Target Inefficiencies:** High capital lockup in slow-moving stock, deep margin collapse on late clearance markdowns (-78.6% margin), and a 3.5x performance spread between stores.

*For full details on product lines, margins, and operational context, see [`docs/BUSINESS_CONTEXT.md`](docs/BUSINESS_CONTEXT.md).*

---

## 📊 Dataset Due Diligence Summary

Before any modeling began, a rigorous audit was conducted across the two source tables spanning **11 months** (June 2025 – April 2026).

| Metric | Sales Ledger (`retail_sales_ml_apl.csv`) | Inventory Ledger (`retail_inventory_ml_apl.csv`) |
| :--- | :--- | :--- |
| **Row Count** | 125,751 rows | 284,755 rows |
| **Dataset Grain** | Daily transaction slice per `(SKU, Store, Date, Sales Type, Return)` | SCD Type 2 state validity interval `[Start Date, End Date]` |
| **Primary Key** | `(Product No, Store, Transaction Date, Sales Type, Is Return)` (100% unique) | `(Product No, Store, Start Date)` (100% unique) |
| **Entity Overlap** | **2,326 SKUs**, **40 Stores**, **30 Suppliers** (100.00% 1:1 match) | **2,326 SKUs**, **40 Stores**, **30 Suppliers** (100.00% 1:1 match) |
| **Hierarchy Match** | 100% exact match across Division → Category → Subcategory → Segment | 100% exact match across Division → Category → Subcategory → Segment |

### Key Business & Financial Baseline Findings
- **Enterprise Financials:** $10.48M total sales revenue | $5.85M COGS | $4.63M gross margin (44.21%).
- **Working Capital Tied Up:** Average standing inventory cost of **$2,404,541.94** (134.9 Days Sales of Inventory / 2.71x turnover).
- **Demand Intermittency:** **98.54% of active SKU × Store series exhibit intermittent demand** (99.588% matrix sparsity).
- **Markdown Margin Collapse:** Full Price yields +48.28% margin; Promo yields +26.69%; Markdown Tier 2 turns negative at -12.96%; Clearance drops to -78.59% (-$23.7K liquidation losses).

*For the full 12-section technical audit, see [`audit/DATASET_AUDIT.md`](audit/DATASET_AUDIT.md).*

---

## 🎯 Platform Vision & Modules

The platform is designed as a unified retail decision-support engine containing three core modules:

```text
                               RAW OPERATIONAL DATA
                                        │
                                        ▼
                             Data Ingestion & Cleaning
                                        │
                                        ▼
                          Intermittent Demand Engine
                         (Croston / Tweedie LightGBM)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        [Module 1: Inventory (s, S)]             [Module 3: Markdown Advisor]
      Stochastic Reorder Optimization            Clearance Timing Optimization
                    │                                       │
                    ▼                                       ▼
        [Module 2: Store Allocation]            Margin Protection & Liquidation
       Constrained Multi-Store Knapsack
                    │
                    └───────────────────┬───────────────────┘
                                        │
                                        ▼
                            Walk-Forward Backtester
                                        │
                                        ▼
                             QUANTIFIED € IMPACT
```

1. **Smart Inventory Policy Optimizer (s, S):**  
   Calculates safety stocks and dynamic reorder points to reduce standing inventory capital while preserving target service levels (e.g. 95%).
2. **Store Allocation Optimizer:**  
   Solves a constrained integer program (Knapsack / MILP) allocating incoming batches across 40 stores based on sales velocity and margin.
3. **Dynamic Markdown & Clearance Advisor:**  
   Identifies aging inventory and prescribes optimal discount timing before stock triggers negative-margin clearance liquidation.
4. **Historical Counterfactual Backtester (Flagship Feature):**  
   Simulates what would have happened historically under the optimized policy vs. observed history, measuring released capital and stockout prevention.

*For full product and architectural specifications, see [`docs/PLATFORM_SPECIFICATION.md`](docs/PLATFORM_SPECIFICATION.md).*

---

## 🗺️ Phased Implementation Plan

- [x] **Phase 0: Data Due Diligence & System Scoping**
  - Complete technical audit (`audit/DATASET_AUDIT.md`).
  - Architecture and prototype specification (`docs/PLATFORM_SPECIFICATION.md`).
  - Repository structure and environment setup.
- [ ] **Phase 1: Smart Inventory Optimizer (Core Demo)**
  - Data pipelines and censored demand adjustment (`src/data/`).
  - Intermittent demand forecasting engine (`src/forecasting/`).
  - Stochastic $(s, S)$ inventory optimization policy (`src/optimization/`).
  - Daily walk-forward backtesting simulator (`src/simulation/`).
  - Interactive decision dashboard.
- [ ] **Phase 2: Multi-Store Stock Allocation**
  - Constrained allocation optimizer across 40 storefronts.
- [ ] **Phase 3: Markdown & Liquidation Engine**
  - Inventory aging tracker and clearance discount advisor.

---

## 🛠️ Quickstart & Reproducibility

### 1. Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd <repo-folder>

# Activate Python 3.11+ virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pandas numpy scipy matplotlib tabulate
```

### 2. Run Data Audit Scripts
```bash
# Run basic dataset profiling
python audit/scripts/01_basic_audit.py

# Run grain and temporal join audit
python audit/scripts/02_grain_and_join_audit.py

# Run demand intermittency and financial deep dive
python audit/scripts/05_demand_and_financial_deep_dive.py

# Reconstruct 5 representative case studies and generate charts
python audit/scripts/04_case_study_reconstruction.py
```
Generated audit charts are saved to `audit/reports/figures/`.
