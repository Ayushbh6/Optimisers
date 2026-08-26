import pandas as pd
import numpy as np

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"

def analyze_inventory_dynamics():
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)
    
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2099-12-31'}))
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])
    
    # 1. Negative Inventory & Cost of Stocks Investigation
    print("=== 1. NEGATIVE INVENTORY & COST OF STOCKS AUDIT ===")
    neg_qty = inv_df[inv_df['Qty on hand'] < 0]
    print(f"Total Negative Qty on hand rows: {len(neg_qty):,} ({len(neg_qty)/len(inv_df)*100:.3f}%)")
    print(f"Distribution of Negative Qty on Hand:")
    print(neg_qty['Qty on hand'].value_counts().sort_index())
    
    neg_cost = inv_df[inv_df['Cost of Stocks'] < 0]
    print(f"\nTotal Negative Cost of Stocks rows: {len(neg_cost):,} ({len(neg_cost)/len(inv_df)*100:.3f}%)")
    print(f"Breakdown of Negative Cost of Stocks by Qty on hand status:")
    print(f"  When Qty on hand < 0: {(neg_cost['Qty on hand'] < 0).sum():,}")
    print(f"  When Qty on hand == 0: {(neg_cost['Qty on hand'] == 0).sum():,}")
    print(f"  When Qty on hand > 0: {(neg_cost['Qty on hand'] > 0).sum():,}  <-- (Negative Cost of Stocks despite POSITIVE stock!)")
    
    # Let's inspect rows with positive Qty on hand but negative Cost of Stocks
    pos_qty_neg_cost = inv_df[(inv_df['Qty on hand'] > 0) & (inv_df['Cost of Stocks'] < 0)]
    print(f"\nSample rows with Qty on hand > 0 but Cost of Stocks < 0:")
    print(pos_qty_neg_cost[['Start Date', 'End Date', 'Product No', 'Store', 'Qty on hand', 'Stock Unit Cost Price', 'Cost of Stocks', 'Stocks Selling Amount']].head(10))

    # 2. Mathematical Reconciliation of Inventory Financials
    print("\n=== 2. MATHEMATICAL RECONCILIATION: INVENTORY FINANCIALS ===")
    # Check: Stocks Selling Amount == Qty on hand * Stock Unit Selling Price
    expected_stocks_selling = inv_df['Qty on hand'] * inv_df['Stock Unit Selling Price']
    selling_diff = (inv_df['Stocks Selling Amount'] - expected_stocks_selling).abs()
    print(f"Stocks Selling Amount == Qty on hand * Stock Unit Selling Price:")
    print(f"  Exact matches (diff < 0.01): {(selling_diff < 0.01).sum():,} ({(selling_diff < 0.01).mean()*100:.2f}%)")
    print(f"  Mismatches: {(selling_diff >= 0.01).sum():,} ({(selling_diff >= 0.01).mean()*100:.2f}%)")
    if (selling_diff >= 0.01).sum() > 0:
        print("  Sample selling amount mismatches:")
        print(inv_df[selling_diff >= 0.01][['Qty on hand', 'Stock Unit Selling Price', 'Stocks Selling Amount']].head())

    # Check: Cost of Stocks == Qty on hand * Stock Unit Cost Price
    expected_stocks_cost = inv_df['Qty on hand'] * inv_df['Stock Unit Cost Price']
    cost_diff = (inv_df['Cost of Stocks'] - expected_stocks_cost).abs()
    print(f"\nCost of Stocks == Qty on hand * Stock Unit Cost Price:")
    print(f"  Exact matches (diff < 0.01): {(cost_diff < 0.01).sum():,} ({(cost_diff < 0.01).mean()*100:.2f}%)")
    print(f"  Mismatches: {(cost_diff >= 0.01).sum():,} ({(cost_diff >= 0.01).mean()*100:.2f}%)")
    if (cost_diff >= 0.01).sum() > 0:
        print("  Sample cost of stocks mismatches:")
        mismatch_sample = inv_df[cost_diff >= 0.01][['Start Date', 'Product No', 'Store', 'Qty on hand', 'Stock Unit Cost Price', 'Cost of Stocks']]
        print(mismatch_sample.head(10))
        # Why is there a mismatch? Let's check the ratio
        calc_unit_cost = inv_df.loc[cost_diff >= 0.01, 'Cost of Stocks'] / inv_df.loc[cost_diff >= 0.01, 'Qty on hand']
        print("  Derived unit cost (Cost of Stocks / Qty on hand) vs Stock Unit Cost Price for mismatches:")
        print(pd.DataFrame({'Derived': calc_unit_cost, 'Stored': inv_df.loc[cost_diff >= 0.01, 'Stock Unit Cost Price']}).head(10))

    # 3. Mathematical Reconciliation of Sales Financials
    print("\n=== 3. MATHEMATICAL RECONCILIATION: SALES FINANCIALS ===")
    # Derived Unit Price = Sales Amount / Qty Sold
    valid_sales = sales_df[sales_df['Qty Sold'] != 0].copy()
    valid_sales['derived_unit_price'] = valid_sales['Sales Amount'] / valid_sales['Qty Sold']
    valid_sales['derived_unit_cogs'] = valid_sales['Cogs'] / valid_sales['Qty Sold']
    print(f"Sales derived unit price summary:")
    print(valid_sales['derived_unit_price'].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    print(f"Sales derived unit cogs summary:")
    print(valid_sales['derived_unit_cogs'].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    
    # Check if Gross Margin (Sales Amount - Cogs) is negative in sales
    valid_sales['gross_margin'] = valid_sales['Sales Amount'] - valid_sales['Cogs']
    valid_sales['margin_pct'] = np.where(valid_sales['Sales Amount'] != 0, valid_sales['gross_margin'] / valid_sales['Sales Amount'], np.nan)
    print(f"\nGross Margin Summary (Non-return sales):")
    non_return_sales = valid_sales[valid_sales['Is Return'] == 0]
    print(non_return_sales['gross_margin'].describe())
    print(f"Non-return sales with negative gross margin (sold below cost): {(non_return_sales['gross_margin'] < 0).sum():,} ({(non_return_sales['gross_margin'] < 0).mean()*100:.2f}%)")
    print(f"Breakdown of negative margin by Sales Type:")
    print(non_return_sales[non_return_sales['gross_margin'] < 0]['Sales Type'].value_counts())

    # 4. Inventory Depletion and Replenishment Dynamics
    print("\n=== 4. INVENTORY DEPLETION AND REPLENISHMENT RECONCILIATION ===")
    # Sort inventory
    inv_sorted = inv_df.sort_values(['Product No', 'Store', 'Start Date']).copy()
    inv_sorted['prev_qty'] = inv_sorted.groupby(['Product No', 'Store'])['Qty on hand'].shift(1)
    inv_sorted['qty_delta'] = inv_sorted['Qty on hand'] - inv_sorted['prev_qty']
    
    # State transitions
    transitions = inv_sorted[inv_sorted['prev_qty'].notnull()].copy()
    print(f"Total inventory state transitions: {len(transitions):,}")
    print(f"  Qty Increase (Potential Replenishment / Inbound / Return): {(transitions['qty_delta'] > 0).sum():,} ({(transitions['qty_delta'] > 0).mean()*100:.2f}%)")
    print(f"  Qty Decrease (Potential Sale / Outbound / Shrink / Transfer): {(transitions['qty_delta'] < 0).sum():,} ({(transitions['qty_delta'] < 0).mean()*100:.2f}%)")
    print(f"  Qty Unchanged (Price change / Status change / Batch snapshot): {(transitions['qty_delta'] == 0).sum():,} ({(transitions['qty_delta'] == 0).mean()*100:.2f}%)")
    
    print("\nDistribution of Qty Increases (Replenishments):")
    print(transitions[transitions['qty_delta'] > 0]['qty_delta'].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    print(transitions[transitions['qty_delta'] > 0]['qty_delta'].value_counts().head(10))

    print("\nDistribution of Qty Decreases (Depletions):")
    print(transitions[transitions['qty_delta'] < 0]['qty_delta'].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    print(transitions[transitions['qty_delta'] < 0]['qty_delta'].value_counts().head(10))

if __name__ == '__main__':
    analyze_inventory_dynamics()
