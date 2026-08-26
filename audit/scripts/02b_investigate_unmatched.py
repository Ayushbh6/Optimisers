import pandas as pd
import numpy as np
import sqlite3

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"

def investigate_zero_matches_and_transitions():
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)
    
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2099-12-31'}))
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])

    # Group inventory by Product No + Store to see date coverage
    inv_coverage = inv_df.groupby(['Product No', 'Store']).agg(
        min_start=('Start Date', 'min'),
        max_end=('End Date_parsed', 'max'),
        row_count=('Start Date', 'count'),
        has_open_ended=('End Date', lambda x: (x == '9999-12-31').any())
    ).reset_index()

    sales_coverage = sales_df.groupby(['Product No', 'Store']).agg(
        min_sale_date=('Transaction Date', 'min'),
        max_sale_date=('Transaction Date', 'max'),
        sales_row_count=('Transaction Date', 'count'),
        total_qty_sold=('Qty Sold', 'sum')
    ).reset_index()

    comp = pd.merge(sales_coverage, inv_coverage, on=['Product No', 'Store'], how='outer')
    print(f"Total (Product No, Store) pairs in Sales: {len(sales_coverage):,}")
    print(f"Total (Product No, Store) pairs in Inventory: {len(inv_coverage):,}")
    print(f"Pairs in both: {len(comp.dropna(subset=['sales_row_count', 'row_count'])):,}")
    print(f"Pairs in Sales but NOT Inventory: {comp['row_count'].isnull().sum():,}")
    print(f"Pairs in Inventory but NOT Sales: {comp['sales_row_count'].isnull().sum():,}")

    # For paired combinations, check if sale dates are BEFORE min inventory date or AFTER max inventory date or in GAPS
    conn = sqlite3.connect(":memory:")
    inv_df[['Product No', 'Store', 'Start Date', 'End Date', 'Stock Status', 'Qty on hand', 'Stock Unit Selling Price', 'Cost of Stocks']].to_sql('inventory', conn, index=False)
    sales_df[['Transaction Date', 'Product No', 'Store', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs']].to_sql('sales', conn, index=False)

    conn.execute("CREATE INDEX idx_inv ON inventory ([Product No], [Store], [Start Date], [End Date]);")
    conn.execute("CREATE INDEX idx_sales ON sales ([Product No], [Store], [Transaction Date]);")

    unmatched_query = """
    SELECT 
        s.[Transaction Date],
        s.[Product No],
        s.[Store],
        s.[Sales Type],
        s.[Qty Sold],
        s.[Sales Amount],
        s.[Is Return],
        (SELECT MIN(date(i.[Start Date])) FROM inventory i WHERE i.[Product No] = s.[Product No] AND i.[Store] = s.[Store]) AS min_inv_start,
        (SELECT MAX(date(CASE WHEN i.[End Date] = '9999-12-31' THEN '2099-12-31' ELSE i.[End Date] END)) FROM inventory i WHERE i.[Product No] = s.[Product No] AND i.[Store] = s.[Store]) AS max_inv_end,
        (SELECT COUNT(*) FROM inventory i WHERE i.[Product No] = s.[Product No] AND i.[Store] = s.[Store]) AS total_inv_records
    FROM sales s
    LEFT JOIN inventory i
        ON s.[Product No] = i.[Product No]
        AND s.[Store] = i.[Store]
        AND date(s.[Transaction Date]) >= date(i.[Start Date])
        AND date(s.[Transaction Date]) <= date(CASE WHEN i.[End Date] = '9999-12-31' THEN '2099-12-31' ELSE i.[End Date] END)
    WHERE i.[Start Date] IS NULL;
    """
    unmatched_df = pd.read_sql_query(unmatched_query, conn)
    print(f"\nTotal Unmatched Sales Rows: {len(unmatched_df):,}")
    
    unmatched_df['Transaction Date'] = pd.to_datetime(unmatched_df['Transaction Date'])
    unmatched_df['min_inv_start'] = pd.to_datetime(unmatched_df['min_inv_start'])
    unmatched_df['max_inv_end'] = pd.to_datetime(unmatched_df['max_inv_end'])
    
    before_min = (unmatched_df['Transaction Date'] < unmatched_df['min_inv_start']).sum()
    after_max = (unmatched_df['Transaction Date'] > unmatched_df['max_inv_end']).sum()
    in_gap = len(unmatched_df) - before_min - after_max
    no_inv_at_all = unmatched_df['total_inv_records'].isna().sum()

    print(f"  Sales BEFORE first inventory Start Date: {before_min:,} ({before_min/len(unmatched_df)*100:.2f}%)")
    print(f"  Sales AFTER last inventory End Date: {after_max:,} ({after_max/len(unmatched_df)*100:.2f}%)")
    print(f"  Sales in GAP between inventory intervals: {in_gap:,} ({in_gap/len(unmatched_df)*100:.2f}%)")
    print(f"  Product x Store pairs with NO inventory records at all: {no_inv_at_all:,}")

    # Inspect the "GAP" and "AFTER" situations
    print("\n--- Inspecting why Inventory Ends or has Gaps ---")
    # For a few product-stores, look at all inventory rows vs all sales rows
    sample_pairs = unmatched_df[['Product No', 'Store']].drop_duplicates().head(5)
    for idx, row in sample_pairs.iterrows():
        p, s = row['Product No'], row['Store']
        print(f"\n=======================================================")
        print(f"CASE STUDY: Product {p} at Store {s}")
        print("INVENTORY RECORDS:")
        inv_sub = inv_df[(inv_df['Product No'] == p) & (inv_df['Store'] == s)].sort_values('Start Date')
        print(inv_sub[['Start Date', 'End Date', 'Stock Status', 'Qty on hand', 'Stock Unit Selling Price', 'Cost of Stocks', 'Stocks Selling Amount']].to_string())
        print("\nSALES RECORDS:")
        sales_sub = sales_df[(sales_df['Product No'] == p) & (sales_df['Store'] == s)].sort_values('Transaction Date')
        print(sales_sub[['Transaction Date', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs', 'Number of Transactions']].to_string())

if __name__ == '__main__':
    investigate_zero_matches_and_transitions()
