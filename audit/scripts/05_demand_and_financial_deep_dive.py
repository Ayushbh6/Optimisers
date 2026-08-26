import pandas as pd
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"
PLOTS_DIR = "audit/reports/figures"
os.makedirs(PLOTS_DIR, exist_ok=True)

def analyze_demand_and_financials():
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)
    
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2026-06-01'}))
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])

    print("========================================================")
    print("SECTION 6: DEMAND CHARACTERISTICS DEEP DIVE")
    print("========================================================")

    # Total grid size: 2,326 products x 40 stores = 93,040 potential series
    # Date range: 326 unique sales dates (spanning 2025-06-01 to 2026-04-24 = 328 calendar days)
    total_calendar_days = (sales_df['Transaction Date'].max() - sales_df['Transaction Date'].min()).days + 1
    total_potential_matrix_cells = 2326 * 40 * total_calendar_days
    observed_sales_rows = len(sales_df)
    
    print(f"Total Products: 2,326 | Total Stores: 40 | Total Days: {total_calendar_days}")
    print(f"Total Potential (Product x Store x Day) cells: {total_potential_matrix_cells:,}")
    print(f"Observed Non-Zero Sales Transactions: {observed_sales_rows:,}")
    print(f"Global Demand Matrix Sparsity (Zero-Demand Cells): {(1 - (observed_sales_rows / total_potential_matrix_cells)) * 100:.3f}%")

    # Product x Store Level Intermittency Analysis (Syntetos-Boylan Classification)
    # Filter to pairs active in the dataset
    # Aggregate daily sales per (Product, Store)
    daily_ps = sales_df[sales_df['Is Return'] == 0].groupby(['Product No', 'Store', 'Transaction Date'])['Qty Sold'].sum().reset_index()
    
    # Calculate ADI and CV2 for top 1000 pairs and across all pairs
    pair_metrics = []
    
    # Calculate per pair
    ps_groups = daily_ps.groupby(['Product No', 'Store'])
    print(f"Active selling (Product, Store) pairs: {len(ps_groups):,}")

    for (p, s), grp in ps_groups:
        n_sales = len(grp)
        if n_sales < 2:
            adi = total_calendar_days # solitary sale
            cv2 = 0.0
            demand_cat = 'Intermittent'
        else:
            dates = grp['Transaction Date'].sort_values()
            intervals = dates.diff().dt.days.dropna()
            adi = intervals.mean()
            mean_demand = grp['Qty Sold'].mean()
            std_demand = grp['Qty Sold'].std()
            cv2 = (std_demand / mean_demand) ** 2 if mean_demand > 0 else 0.0
            
            # Classification rules (Syntetos & Boylan, 2005)
            # Cutoff ADI = 1.32 (some use 1.32 days between demands)
            # Cutoff CV^2 = 0.49
            if adi < 1.32:
                if cv2 < 0.49:
                    demand_cat = 'Smooth'
                else:
                    demand_cat = 'Erratic'
            else:
                if cv2 < 0.49:
                    demand_cat = 'Intermittent'
                else:
                    demand_cat = 'Lumpy'
                    
        pair_metrics.append({
            'Product No': p,
            'Store': s,
            'n_sales_days': n_sales,
            'total_qty': grp['Qty Sold'].sum(),
            'adi': adi,
            'cv2': cv2,
            'demand_cat': demand_cat
        })

    demand_df = pd.DataFrame(pair_metrics)
    print("\n--- Syntetos-Boylan Demand Categorization ---")
    cat_counts = demand_df['demand_cat'].value_counts()
    print(cat_counts)
    print(demand_df['demand_cat'].value_counts(normalize=True) * 100)
    print("\nADI summary:")
    print(demand_df['adi'].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]))
    print("\nCV^2 summary:")
    print(demand_df['cv2'].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]))

    # Day of week seasonality
    sales_df['DayOfWeek'] = sales_df['Transaction Date'].dt.day_name()
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_stats = sales_df.groupby('DayOfWeek').agg(
        total_qty=('Qty Sold', 'sum'),
        total_revenue=('Sales Amount', 'sum'),
        avg_daily_qty=('Qty Sold', 'mean'),
        transactions=('Number of Transactions', 'sum')
    ).reindex(dow_order)
    print("\n--- Day of Week Distribution ---")
    print(dow_stats)

    # Monthly Trend / Seasonality
    sales_df['YearMonth'] = sales_df['Transaction Date'].dt.to_period('M')
    monthly_stats = sales_df.groupby('YearMonth').agg(
        total_qty=('Qty Sold', 'sum'),
        total_revenue=('Sales Amount', 'sum'),
        total_cogs=('Cogs', 'sum'),
        active_products=('Product No', 'nunique'),
        transactions=('Number of Transactions', 'sum')
    )
    monthly_stats['gross_margin'] = monthly_stats['total_revenue'] - monthly_stats['total_cogs']
    monthly_stats['margin_pct'] = monthly_stats['gross_margin'] / monthly_stats['total_revenue'] * 100
    print("\n--- Monthly Sales Performance & Seasonality ---")
    print(monthly_stats)

    # Product concentration (Pareto 80/20)
    prod_sales = sales_df[sales_df['Is Return'] == 0].groupby('Product No')['Qty Sold'].sum().sort_values(ascending=False)
    cum_pct_sales = (prod_sales.cumsum() / prod_sales.sum()) * 100
    top_20_pct_prods = int(len(prod_sales) * 0.20)
    print(f"\n--- Product Demand Concentration ---")
    print(f"Top 20% of products ({top_20_pct_prods} products) generate {cum_pct_sales.iloc[top_20_pct_prods]:.2f}% of total units sold.")
    top_50_pct_prods = int(len(prod_sales) * 0.50)
    print(f"Top 50% of products generate {cum_pct_sales.iloc[top_50_pct_prods]:.2f}% of total units sold.")

    print("\n========================================================")
    print("SECTION 7: FINANCIAL AUDIT")
    print("========================================================")

    total_sales_amount = sales_df['Sales Amount'].sum()
    total_cogs = sales_df['Cogs'].sum()
    total_gross_margin = total_sales_amount - total_cogs
    margin_pct = (total_gross_margin / total_sales_amount) * 100
    
    print(f"Total Sales Revenue: ${total_sales_amount:,.2f}")
    print(f"Total COGS: ${total_cogs:,.2f}")
    print(f"Total Gross Margin: ${total_gross_margin:,.2f} ({margin_pct:.2f}%)")

    # Breakdown by Sales Type
    sales_by_type = sales_df.groupby('Sales Type').agg(
        row_count=('Qty Sold', 'count'),
        total_qty=('Qty Sold', 'sum'),
        total_revenue=('Sales Amount', 'sum'),
        total_cogs=('Cogs', 'sum')
    )
    sales_by_type['gross_margin'] = sales_by_type['total_revenue'] - sales_by_type['total_cogs']
    sales_by_type['margin_pct'] = (sales_by_type['gross_margin'] / sales_by_type['total_revenue']) * 100
    sales_by_type['avg_unit_selling_price'] = sales_by_type['total_revenue'] / sales_by_type['total_qty']
    sales_by_type['avg_unit_cogs'] = sales_by_type['total_cogs'] / sales_by_type['total_qty']
    print("\n--- Sales & Margin Performance by Sales Type ---")
    print(sales_by_type.to_string())

    # Average Inventory Value over time
    # Let's sample inventory value on the 1st and 15th of each month
    sample_dates = pd.date_range('2025-06-01', '2026-04-20', freq='15D')
    inv_snapshots = []
    
    for sd in sample_dates:
        active_inv = inv_df[(inv_df['Start Date'] <= sd) & (inv_df['End Date_parsed'] >= sd)]
        total_stock_qty = active_inv['Qty on hand'].sum()
        total_stock_cost = active_inv['Cost of Stocks'].sum()
        total_stock_retail = active_inv['Stocks Selling Amount'].sum()
        inv_snapshots.append({
            'date': sd,
            'total_units': total_stock_qty,
            'total_cost_val': total_stock_cost,
            'total_retail_val': total_stock_retail
        })
    inv_snap_df = pd.DataFrame(inv_snapshots)
    print("\n--- Inventory Valuation Over Time (Bi-Weekly Snapshots) ---")
    print(inv_snap_df.to_string())

    avg_inv_cost = inv_snap_df['total_cost_val'].mean()
    annualized_cogs = (total_cogs / 328) * 365
    inventory_turnover = annualized_cogs / avg_inv_cost if avg_inv_cost > 0 else np.nan
    days_sales_inventory = 365 / inventory_turnover if inventory_turnover > 0 else np.nan

    print(f"\nAverage Total Inventory Cost (Stock Value): ${avg_inv_cost:,.2f}")
    print(f"Annualized COGS: ${annualized_cogs:,.2f}")
    print(f"Estimated Inventory Turnover Ratio: {inventory_turnover:.2f}x per year")
    print(f"Estimated Days Sales of Inventory (DSI): {days_sales_inventory:.1f} days")

    # Plot demand & financial figures
    plt.figure(figsize=(10, 4))
    plt.plot(inv_snap_df['date'], inv_snap_df['total_cost_val'] / 1e6, marker='o', color='teal', linewidth=2, label='Total Inventory Cost ($M)')
    plt.plot(inv_snap_df['date'], inv_snap_df['total_retail_val'] / 1e6, marker='s', color='orange', linewidth=2, label='Total Inventory Retail ($M)')
    plt.title('Enterprise Inventory Valuation Over Time (2025-2026)', fontsize=12, fontweight='bold')
    plt.ylabel('Valuation ($ Millions)')
    plt.xlabel('Date')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'inventory_valuation_trend.png'), dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    dow_stats['total_revenue'].plot(kind='bar', color='royalblue', edgecolor='black')
    plt.title('Total Revenue by Day of Week', fontsize=12, fontweight='bold')
    plt.ylabel('Revenue ($)')
    plt.xticks(rotation=0)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'revenue_by_dow.png'), dpi=200)
    plt.close()

    # Save summary json
    results = {
        'financials': {
            'total_sales_amount': total_sales_amount,
            'total_cogs': total_cogs,
            'total_gross_margin': total_gross_margin,
            'margin_pct': margin_pct,
            'avg_inv_cost': avg_inv_cost,
            'annualized_cogs': annualized_cogs,
            'inventory_turnover': inventory_turnover,
            'days_sales_inventory': days_sales_inventory
        },
        'demand_classification': cat_counts.to_dict()
    }
    with open('audit/reports/demand_financial_summary.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved audit/reports/demand_financial_summary.json")

if __name__ == '__main__':
    analyze_demand_and_financials()
