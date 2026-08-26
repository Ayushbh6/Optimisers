import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"
PLOTS_DIR = "audit/reports/figures"
os.makedirs(PLOTS_DIR, exist_ok=True)

def reconstruct_case_studies():
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)
    
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2026-06-01'}))
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])

    # Aggregate sales metrics per product x store
    sales_summary = sales_df.groupby(['Product No', 'Store']).agg(
        total_sales_rows=('Qty Sold', 'count'),
        net_qty_sold=('Qty Sold', 'sum'),
        total_gross_qty=('Qty Sold', lambda x: x[x > 0].sum()),
        return_count=('Is Return', 'sum'),
        promo_count=('Sales Type', lambda x: (x == 'Promo').sum()),
        markdown_count=('Sales Type', lambda x: x.str.contains('Markdown|Clearance').sum()),
        total_sales_amount=('Sales Amount', 'sum'),
        distinct_sales_dates=('Transaction Date', 'nunique')
    ).reset_index()

    inv_summary = inv_df.groupby(['Product No', 'Store']).agg(
        inv_rows=('Qty on hand', 'count'),
        min_qty=('Qty on hand', 'min'),
        max_qty=('Qty on hand', 'max'),
        avg_qty=('Qty on hand', 'mean'),
        has_negative_qty=('Qty on hand', lambda x: (x < 0).any()),
        has_negative_cost=('Cost of Stocks', lambda x: (x < 0).any())
    ).reset_index()

    merged_summary = pd.merge(sales_summary, inv_summary, on=['Product No', 'Store'], how='inner')

    # 1. High Volume Candidate
    high_vol = merged_summary.sort_values('net_qty_sold', ascending=False).iloc[0]
    
    # 2. Low Volume Candidate (e.g. 1-2 sales over the entire 11 months, but several inventory periods)
    low_vol = merged_summary[(merged_summary['net_qty_sold'] == 1) & (merged_summary['inv_rows'] >= 3)].iloc[0]

    # 3. Frequently Promoted Candidate
    promo_cand = merged_summary.sort_values('promo_count', ascending=False).iloc[0]

    # 4. Product with returns
    return_cand = merged_summary.sort_values('return_count', ascending=False).iloc[0]

    # 5. Product with unusual inventory behaviour (e.g. negative stock & negative cost)
    unusual_cand = merged_summary[(merged_summary['has_negative_qty']) & (merged_summary['has_negative_cost'])].sort_values('inv_rows', ascending=False).iloc[0]

    candidates = [
        ("1_high_volume", "High Volume", high_vol),
        ("2_low_volume", "Low Volume", low_vol),
        ("3_frequent_promo", "Frequently Promoted", promo_cand),
        ("4_returns", "Product with Returns", return_cand),
        ("5_unusual_inventory", "Unusual Inventory Behavior", unusual_cand)
    ]

    print("=== SELECTED 5 CASE STUDIES ===")
    for tag, desc, c in candidates:
        print(f"\nCategory: {desc} ({tag})")
        print(f"Product: {c['Product No']}, Store: {c['Store']}")
        print(f"Sales Rows: {c['total_sales_rows']}, Net Qty: {c['net_qty_sold']}, Returns: {c['return_count']}, Promos: {c['promo_count']}, Inv Rows: {c['inv_rows']}, Min Qty: {c['min_qty']}, Max Qty: {c['max_qty']}")

    # Build chronological event histories and plots
    all_case_logs = {}

    for tag, desc, c in candidates:
        p, s = c['Product No'], c['Store']
        
        # Get inv rows
        i_sub = inv_df[(inv_df['Product No'] == p) & (inv_df['Store'] == s)].sort_values('Start Date').copy()
        # Get sales rows
        s_sub = sales_df[(sales_df['Product No'] == p) & (sales_df['Store'] == s)].sort_values('Transaction Date').copy()
        
        # Create full date range
        min_d = min(i_sub['Start Date'].min(), s_sub['Transaction Date'].min())
        max_d = max(i_sub['Start Date'].max(), s_sub['Transaction Date'].max())
        
        # Build daily timeline
        dates = pd.date_range(min_d, max_d, freq='D')
        daily_df = pd.DataFrame({'Date': dates})
        
        # Merge sales on date
        daily_sales = s_sub.groupby('Transaction Date').agg(
            qty_sold=('Qty Sold', 'sum'),
            sales_amount=('Sales Amount', 'sum'),
            cogs=('Cogs', 'sum'),
            is_return=('Is Return', 'max'),
            sales_type=('Sales Type', lambda x: ', '.join(x.unique()))
        ).reset_index()
        
        daily_df = pd.merge(daily_df, daily_sales, left_on='Date', right_on='Transaction Date', how='left')
        daily_df['qty_sold'] = daily_df['qty_sold'].fillna(0)
        daily_df['sales_amount'] = daily_df['sales_amount'].fillna(0)
        daily_df['cogs'] = daily_df['cogs'].fillna(0)
        daily_df['is_return'] = daily_df['is_return'].fillna(0)
        
        # For each date, find the active inventory interval
        inv_qty_list = []
        inv_status_list = []
        inv_price_list = []
        inv_cost_list = []
        inv_val_list = []
        
        for d in dates:
            matching_inv = i_sub[(i_sub['Start Date'] <= d) & (i_sub['End Date_parsed'] >= d)]
            if len(matching_inv) > 0:
                inv_qty_list.append(matching_inv.iloc[0]['Qty on hand'])
                inv_status_list.append(matching_inv.iloc[0]['Stock Status'])
                inv_price_list.append(matching_inv.iloc[0]['Stock Unit Selling Price'])
                inv_cost_list.append(matching_inv.iloc[0]['Stock Unit Cost Price'])
                inv_val_list.append(matching_inv.iloc[0]['Cost of Stocks'])
            else:
                inv_qty_list.append(np.nan)
                inv_status_list.append('No Record (Stockout/Gap)')
                inv_price_list.append(np.nan)
                inv_cost_list.append(np.nan)
                inv_val_list.append(np.nan)
                
        daily_df['qty_on_hand'] = inv_qty_list
        daily_df['stock_status'] = inv_status_list
        daily_df['stock_unit_price'] = inv_price_list
        daily_df['stock_unit_cost'] = inv_cost_list
        daily_df['cost_of_stocks'] = inv_val_list

        # Save case log
        all_case_logs[tag] = {
            'metadata': c.to_dict(),
            'inventory_raw': i_sub[['Start Date', 'End Date', 'Stock Status', 'Qty on hand', 'Stock Unit Selling Price', 'Cost of Stocks', 'Stocks Selling Amount']].to_dict(orient='records'),
            'sales_raw': s_sub[['Transaction Date', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs', 'Number of Transactions']].to_dict(orient='records'),
            'daily_reconstructed': daily_df[daily_df['qty_sold'] != 0].to_dict(orient='records')
        }

        # Plot time series
        fig, ax1 = plt.subplots(figsize=(12, 5))
        
        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Qty on Hand (Inventory)', color=color)
        ax1.step(daily_df['Date'], daily_df['qty_on_hand'], where='post', color=color, label='Inventory Qty on Hand', linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, alpha=0.3)
        
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Daily Qty Sold / Returned', color=color)
        
        # Separate positive sales and returns
        pos_sales = daily_df[daily_df['qty_sold'] > 0]
        neg_sales = daily_df[daily_df['qty_sold'] < 0]
        
        if len(pos_sales) > 0:
            ax2.bar(pos_sales['Date'], pos_sales['qty_sold'], width=1.5, color='tab:red', alpha=0.7, label='Sale (+Qty)')
        if len(neg_sales) > 0:
            ax2.bar(neg_sales['Date'], neg_sales['qty_sold'], width=1.5, color='tab:purple', alpha=0.7, label='Return (-Qty)')
            
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title(f"Case Study: {desc} | {p} @ {s}", fontsize=13, fontweight='bold')
        fig.tight_layout()
        plot_path = os.path.join(PLOTS_DIR, f"case_{tag}.png")
        plt.savefig(plot_path, dpi=200)
        plt.close()
        print(f"Saved plot: {plot_path}")

    # Output detailed logs for report
    import json
    with open("audit/reports/case_studies_data.json", "w") as f:
        json.dump(all_case_logs, f, indent=2, default=str)
    print("Saved audit/reports/case_studies_data.json")

if __name__ == '__main__':
    reconstruct_case_studies()
