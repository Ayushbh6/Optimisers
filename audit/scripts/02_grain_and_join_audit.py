import pandas as pd
import numpy as np
import json

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"

def run_grain_and_join_audit():
    print("Loading datasets...")
    inv_df = pd.read_csv(INVENTORY_PATH, low_memory=False)
    sales_df = pd.read_csv(SALES_PATH, low_memory=False)

    print("\n========================================================")
    print("SECTION 2: GRAIN AUDIT")
    print("========================================================")

    # Sales Grain Investigation
    print("\n--- SALES GRAIN INVESTIGATION ---")
    sales_df['Transaction Date'] = pd.to_datetime(sales_df['Transaction Date'])
    
    total_sales_rows = len(sales_df)
    unique_prod_store_date = sales_df.groupby(['Product No', 'Store', 'Transaction Date']).ngroups
    print(f"Total Sales rows: {total_sales_rows:,}")
    print(f"Unique (Product No, Store, Transaction Date) tuples: {unique_prod_store_date:,}")
    print(f"Rows per (Product No, Store, Transaction Date): {total_sales_rows / unique_prod_store_date:.4f}")
    
    # Check what causes duplicates on (Product, Store, Date)
    prod_store_date_counts = sales_df.groupby(['Product No', 'Store', 'Transaction Date']).size()
    dupe_keys = prod_store_date_counts[prod_store_date_counts > 1]
    print(f"Number of (Product, Store, Date) keys with multiple rows: {len(dupe_keys):,} ({len(dupe_keys)/unique_prod_store_date*100:.2f}%)")
    print(f"Max rows for a single (Product, Store, Date): {prod_store_date_counts.max()}")
    
    if len(dupe_keys) > 0:
        sample_dupe_key = dupe_keys.index[0]
        print(f"\nSample multi-row (Product, Store, Date): {sample_dupe_key}")
        sample_rows = sales_df[(sales_df['Product No'] == sample_dupe_key[0]) & 
                               (sales_df['Store'] == sample_dupe_key[1]) & 
                               (sales_df['Transaction Date'] == sample_dupe_key[2])]
        print(sample_rows[['Transaction Date', 'Product No', 'Store', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs', 'Number of Transactions']])
        
        # Test candidate composite primary keys for sales
        for cand in [
            ['Product No', 'Store', 'Transaction Date'],
            ['Product No', 'Store', 'Transaction Date', 'Sales Type'],
            ['Product No', 'Store', 'Transaction Date', 'Sales Type', 'Is Return'],
            ['Product No', 'Store', 'Transaction Date', 'Sales Type', 'Is Return', 'Sales Amount'],
            ['Product No', 'Store', 'Transaction Date', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs']
        ]:
            n_grp = sales_df.groupby(cand).ngroups
            print(f"Candidate key {cand}: {n_grp:,} unique combinations out of {total_sales_rows:,} rows (Duplication: {total_sales_rows - n_grp:,})")

    # Sales: Number of Transactions vs Qty Sold
    print("\n--- Sales: Relationship between Number of Transactions and Qty Sold ---")
    print(sales_df.groupby(['Number of Transactions', 'Qty Sold', 'Is Return']).size().reset_index(name='count').head(20).to_string())

    # Inventory Grain Investigation
    print("\n--- INVENTORY GRAIN INVESTIGATION ---")
    inv_df['Start Date'] = pd.to_datetime(inv_df['Start Date'])
    inv_df['End Date_parsed'] = pd.to_datetime(inv_df['End Date'].replace({'9999-12-31': '2099-12-31'}))
    
    total_inv_rows = len(inv_df)
    unique_inv_prod_store = inv_df.groupby(['Product No', 'Store']).ngroups
    print(f"Total Inventory rows: {total_inv_rows:,}")
    print(f"Unique (Product No, Store) pairs: {unique_inv_prod_store:,}")
    print(f"Average inventory rows per (Product, Store): {total_inv_rows / unique_inv_prod_store:.2f}")

    # Check primary key candidates for inventory
    for cand in [
        ['Product No', 'Store', 'Start Date'],
        ['Product No', 'Store', 'Start Date', 'End Date'],
        ['Product No', 'Store', 'Start Date', 'Stock Status'],
        ['Product No', 'Store', 'Start Date', 'End Date', 'Stock Status']
    ]:
        n_grp = inv_df.groupby(cand).ngroups
        print(f"Inventory Candidate key {cand}: {n_grp:,} unique out of {total_inv_rows:,} rows (Duplication: {total_inv_rows - n_grp:,})")

    # Analyze interval properties per (Product, Store)
    print("\n--- Analyzing Inventory Intervals & Continuity (SCD Type 2 vs Snapshots) ---")
    # Sort inventory by Product, Store, Start Date
    inv_sorted = inv_df.sort_values(['Product No', 'Store', 'Start Date', 'End Date_parsed']).copy()
    
    # Calculate previous end date and next start date within each Product x Store
    inv_sorted['prev_end'] = inv_sorted.groupby(['Product No', 'Store'])['End Date_parsed'].shift(1)
    inv_sorted['prev_start'] = inv_sorted.groupby(['Product No', 'Store'])['Start Date'].shift(1)
    inv_sorted['next_start'] = inv_sorted.groupby(['Product No', 'Store'])['Start Date'].shift(-1)
    
    # Check overlap: is current Start Date <= prev End Date?
    # Note: If End Date is inclusive, next_start should be prev_end + 1 day
    # Let's inspect differences between End Date and next Start Date
    diff_to_next = (inv_sorted['next_start'] - inv_sorted['End Date_parsed']).dt.days
    print("\nDifference in days between End Date and next row Start Date (sample distribution):")
    print(diff_to_next.value_counts(dropna=False).head(15))
    
    diff_from_prev_start = (inv_sorted['Start Date'] - inv_sorted['prev_start']).dt.days
    print("\nDifference in days between consecutive Start Dates (sample distribution):")
    print(diff_from_prev_start.value_counts(dropna=False).head(15))
    
    # Check duration of intervals (End Date - Start Date in days)
    interval_durations = (inv_sorted[inv_sorted['End Date'] != '9999-12-31']['End Date_parsed'] - inv_sorted[inv_sorted['End Date'] != '9999-12-31']['Start Date']).dt.days
    print(f"\nInterval Durations (excluding 9999-12-31, total={len(interval_durations):,} rows):")
    print(interval_durations.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]))
    print("\nMost common interval durations in days:")
    print(interval_durations.value_counts().head(10))

    # Open-ended records (9999-12-31)
    open_ended = inv_df[inv_df['End Date'] == '9999-12-31']
    print(f"\nOpen-ended records (End Date = 9999-12-31): {len(open_ended):,} ({len(open_ended)/len(inv_df)*100:.2f}%)")
    print(f"Unique (Product No, Store) in open-ended records: {open_ended.groupby(['Product No', 'Store']).ngroups:,} vs total {unique_inv_prod_store:,}")

    # Check what triggers a new inventory record:
    # Does Qty on hand change? Stock Status change? Price change? Cost change?
    inv_sorted['prev_qty'] = inv_sorted.groupby(['Product No', 'Store'])['Qty on hand'].shift(1)
    inv_sorted['prev_status'] = inv_sorted.groupby(['Product No', 'Store'])['Stock Status'].shift(1)
    inv_sorted['prev_price'] = inv_sorted.groupby(['Product No', 'Store'])['Stock Unit Selling Price'].shift(1)
    inv_sorted['prev_cost'] = inv_sorted.groupby(['Product No', 'Store'])['Stock Unit Cost Price'].shift(1)
    
    subsequent_rows = inv_sorted[inv_sorted['prev_start'].notnull()].copy()
    print(f"\nTotal subsequent inventory state transitions: {len(subsequent_rows):,}")
    qty_changed = (subsequent_rows['Qty on hand'] != subsequent_rows['prev_qty'])
    status_changed = (subsequent_rows['Stock Status'] != subsequent_rows['prev_status'])
    price_changed = (subsequent_rows['Stock Unit Selling Price'] != subsequent_rows['prev_price'])
    cost_changed = (subsequent_rows['Stock Unit Cost Price'] != subsequent_rows['prev_cost'])
    
    print(f"  Transitions with Qty on Hand change: {qty_changed.sum():,} ({qty_changed.mean()*100:.2f}%)")
    print(f"  Transitions with Stock Status change: {status_changed.sum():,} ({status_changed.mean()*100:.2f}%)")
    print(f"  Transitions with Selling Price change: {price_changed.sum():,} ({price_changed.mean()*100:.2f}%)")
    print(f"  Transitions with Cost Price change: {cost_changed.sum():,} ({cost_changed.mean()*100:.2f}%)")
    any_change = qty_changed | status_changed | price_changed | cost_changed
    print(f"  Transitions with ANY of the 4 changed: {any_change.sum():,} ({any_change.mean()*100:.2f}%)")
    print(f"  Transitions with NONE of the 4 changed: {(~any_change).sum():,} ({(~any_change).mean()*100:.2f}%)")

    print("\n========================================================")
    print("SECTION 3: DATASET CONNECTION & TEMPORAL JOIN AUDIT")
    print("========================================================")

    # 1. Key Overlap
    sales_prods = set(sales_df['Product No'].unique())
    inv_prods = set(inv_df['Product No'].unique())
    print(f"\nUnique Products: Sales={len(sales_prods):,}, Inventory={len(inv_prods):,}")
    print(f"Sales products appearing in Inventory: {len(sales_prods.intersection(inv_prods)) / len(sales_prods)*100:.2f}% ({len(sales_prods.intersection(inv_prods)):,}/{len(sales_prods):,})")
    print(f"Inventory products appearing in Sales: {len(inv_prods.intersection(sales_prods)) / len(inv_prods)*100:.2f}% ({len(inv_prods.intersection(sales_prods)):,}/{len(inv_prods):,})")
    
    sales_stores = set(sales_df['Store'].unique())
    inv_stores = set(inv_df['Store'].unique())
    print(f"\nUnique Stores: Sales={len(sales_stores):,}, Inventory={len(inv_stores):,}")
    print(f"Sales stores in Inventory: {len(sales_stores.intersection(inv_stores)) / len(sales_stores)*100:.2f}%")
    print(f"Inventory stores in Sales: {len(inv_stores.intersection(sales_stores)) / len(inv_stores)*100:.2f}%")

    sales_suppliers = set(sales_df['Supplier'].unique())
    inv_suppliers = set(inv_df['Supplier'].unique())
    print(f"\nUnique Suppliers: Sales={len(sales_suppliers):,}, Inventory={len(inv_suppliers):,}")
    print(f"Sales suppliers in Inventory: {len(sales_suppliers.intersection(inv_suppliers)) / len(sales_suppliers)*100:.2f}%")

    # Check hierarchy consistency between tables for identical Product No
    print("\n--- Attribute Consistency per Product No ---")
    prod_attrs = ['Supplier', 'Product Description', 'Product Division', 'Product Category', 'Product Subcategory', 'Product Segment']
    
    # Aggregate product mapping from both
    sales_prod_map = sales_df[['Product No'] + prod_attrs].drop_duplicates()
    inv_prod_map = inv_df[['Product No'] + prod_attrs].drop_duplicates()
    
    print(f"Sales distinct (Product No, Attributes): {len(sales_prod_map):,} (1:1 with Product No: {len(sales_prod_map) == len(sales_prods)})")
    print(f"Inventory distinct (Product No, Attributes): {len(inv_prod_map):,} (1:1 with Product No: {len(inv_prod_map) == len(inv_prods)})")
    
    merged_prod_map = pd.merge(sales_prod_map, inv_prod_map, on='Product No', suffixes=('_sales', '_inv'))
    print(f"Merged product mapping rows: {len(merged_prod_map):,}")
    for attr in prod_attrs:
        matches = (merged_prod_map[f'{attr}_sales'] == merged_prod_map[f'{attr}_inv']).sum()
        pct = matches / len(merged_prod_map) * 100
        print(f"  Consistency for '{attr}': {pct:.2f}% ({matches:,}/{len(merged_prod_map):,})")

    # 2. Temporal Join Testing
    print("\n--- TEMPORAL JOIN: Start Date <= Transaction Date <= End Date ---")
    # For each row in sales_df, how many matching inventory records exist for the same Product No & Store?
    # Let's perform an interval merge
    
    # We can do this efficiently using duckdb or pandas merge_asof or SQL / cross-merge on Product+Store
    # Since dataset is moderate (125k sales rows, 285k inventory rows), let's use pandas or duckdb
    import sqlite3
    conn = sqlite3.connect(":memory:")
    
    # Create tables
    inv_df[['Product No', 'Store', 'Start Date', 'End Date', 'Stock Status', 'Qty on hand', 'Stock Unit Selling Price', 'Cost of Stocks']].to_sql('inventory', conn, index=False)
    sales_df[['Transaction Date', 'Product No', 'Store', 'Sales Type', 'Is Return', 'Qty Sold', 'Sales Amount', 'Cogs']].to_sql('sales', conn, index=False)
    
    # Create indexes for speed
    conn.execute("CREATE INDEX idx_inv ON inventory ([Product No], [Store], [Start Date], [End Date]);")
    conn.execute("CREATE INDEX idx_sales ON sales ([Product No], [Store], [Transaction Date]);")
    
    print("Executing interval join in SQLite...")
    query = """
    SELECT 
        s.[Transaction Date],
        s.[Product No],
        s.[Store],
        s.[Sales Type],
        s.[Qty Sold],
        COUNT(i.[Start Date]) as match_count
    FROM sales s
    LEFT JOIN inventory i
        ON s.[Product No] = i.[Product No]
        AND s.[Store] = i.[Store]
        AND date(s.[Transaction Date]) >= date(i.[Start Date])
        AND date(s.[Transaction Date]) <= date(CASE WHEN i.[End Date] = '9999-12-31' THEN '2099-12-31' ELSE i.[End Date] END)
    GROUP BY s.rowid;
    """
    match_df = pd.read_sql_query(query, conn)
    
    print(f"\nTotal Sales rows evaluated: {len(match_df):,}")
    match_counts = match_df['match_count'].value_counts().sort_index()
    print("Temporal Match Distribution:")
    for count, n in match_counts.items():
        print(f"  Matching inventory records = {count}: {n:,} rows ({n/len(match_df)*100:.4f}%)")
        
    # Investigate 0 matches if any
    zero_matches = match_df[match_df['match_count'] == 0]
    print(f"\nZero-match sales rows: {len(zero_matches):,}")
    if len(zero_matches) > 0:
        print("Sample zero-match sales rows:")
        print(zero_matches.head(10))
        
    # Investigate >1 matches if any
    multi_matches = match_df[match_df['match_count'] > 1]
    print(f"\nMulti-match sales rows: {len(multi_matches):,}")
    if len(multi_matches) > 0:
        print("Sample multi-match sales rows:")
        print(multi_matches.head(10))
        # Inspect full join for one multi-match
        sample_multi = multi_matches.iloc[0]
        inspect_q = f"""
        SELECT 
            s.[Transaction Date], s.[Product No], s.[Store], s.[Sales Type], s.[Qty Sold],
            i.[Start Date], i.[End Date], i.[Stock Status], i.[Qty on hand]
        FROM sales s
        JOIN inventory i
            ON s.[Product No] = i.[Product No]
            AND s.[Store] = i.[Store]
            AND date(s.[Transaction Date]) >= date(i.[Start Date])
            AND date(s.[Transaction Date]) <= date(CASE WHEN i.[End Date] = '9999-12-31' THEN '2099-12-31' ELSE i.[End Date] END)
        WHERE s.[Product No] = '{sample_multi['Product No']}' 
          AND s.[Store] = '{sample_multi['Store']}' 
          AND s.[Transaction Date] = '{sample_multi['Transaction Date']}';
        """
        sample_multi_rows = pd.read_sql_query(inspect_q, conn)
        print("Multi-match join detail:")
        print(sample_multi_rows)

if __name__ == '__main__':
    run_grain_and_join_audit()
