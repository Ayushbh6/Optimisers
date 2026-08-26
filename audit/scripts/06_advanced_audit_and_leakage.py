import pandas as pd
import numpy as np
import json

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"

def advanced_audit():
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)
    
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2026-06-01'}))
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])

    print("========================================================")
    print("STORE LEVEL DISTRIBUTION & DIFFERENCES")
    print("========================================================")
    store_sales = sales_df.groupby('Store').agg(
        total_revenue=('Sales Amount', 'sum'),
        total_units=('Qty Sold', 'sum'),
        total_cogs=('Cogs', 'sum'),
        active_products=('Product No', 'nunique'),
        transactions=('Number of Transactions', 'sum')
    )
    store_sales['gross_margin'] = store_sales['total_revenue'] - store_sales['total_cogs']
    store_sales['margin_pct'] = store_sales['gross_margin'] / store_sales['total_revenue'] * 100
    store_sales['avg_daily_revenue'] = store_sales['total_revenue'] / 328
    store_sales = store_sales.sort_values('total_revenue', ascending=False)
    print("Top 5 Stores by Revenue:")
    print(store_sales.head(5))
    print("\nBottom 5 Stores by Revenue:")
    print(store_sales.tail(5))
    print(f"\nRevenue ratio (Top 1 Store / Bottom 1 Store): {store_sales['total_revenue'].iloc[0] / store_sales['total_revenue'].iloc[-1]:.2f}x")

    print("\n========================================================")
    print("PRODUCT DIVISION & CATEGORY FINANCIAL SUMMARY")
    print("========================================================")
    div_summary = sales_df.groupby('Product Division').agg(
        total_revenue=('Sales Amount', 'sum'),
        total_units=('Qty Sold', 'sum'),
        total_cogs=('Cogs', 'sum'),
        active_products=('Product No', 'nunique')
    )
    div_summary['gross_margin'] = div_summary['total_revenue'] - div_summary['total_cogs']
    div_summary['margin_pct'] = div_summary['gross_margin'] / div_summary['total_revenue'] * 100
    div_summary['rev_share_pct'] = div_summary['total_revenue'] / div_summary['total_revenue'].sum() * 100
    print(div_summary.to_string())

    print("\n========================================================")
    print("PROMOTION & PRICE ELASTICITY CHECK")
    print("========================================================")
    # Compare average price and daily sales velocity for products when on Full Price vs Promo
    promo_prods = sales_df[sales_df['Sales Type'] == 'Promo']['Product No'].unique()
    print(f"Products sold on Promo: {len(promo_prods):,} / 2,326 ({len(promo_prods)/2326*100:.2f}%)")
    
    # Calculate price discount and volume lift on promo
    fp_sales = sales_df[sales_df['Sales Type'] == 'Full Price'].groupby('Product No').agg(
        fp_rev=('Sales Amount', 'sum'),
        fp_units=('Qty Sold', 'sum'),
        fp_days=('Transaction Date', 'nunique')
    )
    pr_sales = sales_df[sales_df['Sales Type'] == 'Promo'].groupby('Product No').agg(
        pr_rev=('Sales Amount', 'sum'),
        pr_units=('Qty Sold', 'sum'),
        pr_days=('Transaction Date', 'nunique')
    )
    promo_comp = pd.merge(fp_sales, pr_sales, on='Product No', how='inner')
    promo_comp['fp_unit_price'] = promo_comp['fp_rev'] / promo_comp['fp_units']
    promo_comp['pr_unit_price'] = promo_comp['pr_rev'] / promo_comp['pr_units']
    promo_comp['discount_pct'] = (1 - (promo_comp['pr_unit_price'] / promo_comp['fp_unit_price'])) * 100
    promo_comp['fp_velocity'] = promo_comp['fp_units'] / promo_comp['fp_days']
    promo_comp['pr_velocity'] = promo_comp['pr_units'] / promo_comp['pr_days']
    promo_comp['volume_lift_pct'] = ((promo_comp['pr_velocity'] / promo_comp['fp_velocity']) - 1) * 100
    
    print("\nPromo vs Full Price Comparison (for products sold in both modes, N = len(promo_comp)):")
    print(f"Count of products with both: {len(promo_comp):,}")
    print(promo_comp[['discount_pct', 'volume_lift_pct', 'fp_unit_price', 'pr_unit_price']].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]))

    print("\n========================================================")
    print("MISSING VARIABLES & RECONSTRUCTION FEASIBILITY")
    print("========================================================")
    missing_vars = {
        "Supplier Lead Times": "ABSENT (No order-to-delivery timestamps, no PO records)",
        "Purchase Orders (PO)": "ABSENT (No PO numbers, order dates, or ordered quantities)",
        "Minimum Order Quantities (MOQ)": "ABSENT (Cannot be observed directly; inferred small batched increments mean MOQ is either 1 or unconstrained at store level)",
        "Supplier Capacity / Bottlenecks": "ABSENT",
        "Warehouse / Shelf Storage Capacity": "ABSENT (Store physical cubic/sqft capacity unknown)",
        "Holding Cost Rate (% / $ / unit / year)": "ABSENT (Requires standard WACC + storage assumption, e.g., 20-25% per annum)",
        "Ordering / Fixed Setup Cost per PO": "ABSENT (Requires standard simulation assumption, e.g. $50-$100/order)",
        "Stockout Penalty / Lost Sales Penalty": "ABSENT (Can only be estimated via unconstrained demand modeling or margin loss)",
        "Inter-store Transfer Costs": "ABSENT (Distance matrix, freight rates, or handling costs missing)",
        "Product Expiry / Shelf Life": "ABSENT (Not perishable; fashion/apparel lifecycle aging instead)",
        "Target Service Levels (SLAs)": "ABSENT (Business policy parameter)"
    }
    for k, v in missing_vars.items():
        print(f"  * {k}: {v}")

    print("\n========================================================")
    print("DATA LEAKAGE & MODELLING TRAPS")
    print("========================================================")
    leakage_points = [
        "1. SCD Type 2 End Date Lookahead Leakage: The `End Date` in the inventory table is determined retrospectively when the next state transition happens. Conditioning on `End Date` during demand forecasting or backtesting leaks future transaction/replenishment timing!",
        "2. Zero-inventory truncation vs Uncensored Demand: Sales only reflect observed demand when stock > 0. Using raw historical sales without adjusting for stockout periods underestimates true unconstrained demand (censored demand bias).",
        "3. Future Price & Markdown Leakage: Using lifecycle markdown flags (e.g. Clearance) before the clearance event actually occurred leaks product obsolescence state.",
        "4. Inferred Replenishment Timing: Replenishments are inferred from positive inventory jumps. If an automated policy uses the exact historical arrival date without lead-time stochasticity, it overestimates supply reliability."
    ]
    for lp in leakage_points:
        print(f"  * {lp}")

    # Save summary
    with open("audit/reports/advanced_audit.json", "w") as f:
        json.dump({
            "store_count": len(store_sales),
            "top_store": store_sales.index[0],
            "bottom_store": store_sales.index[-1],
            "div_summary": div_summary.to_dict(),
            "missing_vars": missing_vars,
            "leakage_points": leakage_points
        }, f, indent=2, default=str)

if __name__ == '__main__':
    advanced_audit()
