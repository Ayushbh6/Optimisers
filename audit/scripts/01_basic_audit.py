import pandas as pd
import numpy as np
import os
import json

INVENTORY_PATH = "data/raw/retail_inventory_ml_apl.csv"
SALES_PATH = "data/raw/retail_sales_ml_apl.csv"

def audit_file(path, name):
    print(f"\n==========================================")
    print(f"AUDITING: {name} ({path})")
    print(f"==========================================")
    
    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"File Size on Disk: {file_size_mb:.2f} MB")
    
    df = pd.read_csv(path, low_memory=False)
    
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Memory Usage: {df.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB")
    
    print("\n--- Column Info & Types ---")
    dtypes_df = pd.DataFrame({
        'Column': df.columns,
        'Dtype': [str(t) for t in df.dtypes],
        'Non-Null Count': [df[c].notnull().sum() for c in df.columns],
        'Null Count': [df[c].isnull().sum() for c in df.columns],
        'Null %': [(df[c].isnull().sum() / len(df)) * 100 for c in df.columns],
        'Unique Count': [df[c].nunique(dropna=False) for c in df.columns],
        'Sample Value': [df[c].dropna().iloc[0] if df[c].notnull().sum() > 0 else 'ALL NULL' for c in df.columns]
    })
    print(dtypes_df.to_string(index=False))
    
    print(f"\nExact Duplicate Rows: {df.duplicated().sum():,}")
    
    # Dates
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'day' in c.lower()]
    print(f"\n--- Date Columns: {date_cols} ---")
    for dc in date_cols:
        parsed_dates = pd.to_datetime(df[dc], errors='coerce')
        nat_count = parsed_dates.isna().sum()
        print(f"Column '{dc}': min = {parsed_dates.min()}, max = {parsed_dates.max()}, NaT count = {nat_count:,}")
    
    # Numeric Columns stats (negatives, zeros, min, max, median, quartiles)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(f"\n--- Numeric Columns Audit ---")
    num_stats = []
    for nc in num_cols:
        s = df[nc].dropna()
        num_stats.append({
            'Column': nc,
            'Min': s.min(),
            'Q01': s.quantile(0.01) if len(s)>0 else None,
            'Q25': s.quantile(0.25) if len(s)>0 else None,
            'Median': s.median() if len(s)>0 else None,
            'Mean': s.mean() if len(s)>0 else None,
            'Q75': s.quantile(0.75) if len(s)>0 else None,
            'Q99': s.quantile(0.99) if len(s)>0 else None,
            'Max': s.max(),
            'Zeros': (s == 0).sum(),
            'Zero %': ((s == 0).sum() / len(df)) * 100,
            'Negatives': (s < 0).sum(),
            'Neg %': ((s < 0).sum() / len(df)) * 100,
        })
    num_stats_df = pd.DataFrame(num_stats)
    print(num_stats_df.to_string(index=False))
    
    # Categoricals inspection
    cat_candidates = [c for c in df.columns if df[c].nunique() < 50 and c not in num_cols] + \
                     [c for c in ['Stock Status', 'Sales Type', 'Store Type', 'Sales Channel', 'Is Return', 'Reason of Return'] if c in df.columns]
    cat_candidates = list(dict.fromkeys(cat_candidates))
    print(f"\n--- Key Categorical Fields Breakdown ---")
    for cc in cat_candidates:
        if cc in df.columns:
            vc = df[cc].value_counts(dropna=False)
            print(f"\nDistribution for '{cc}':")
            print(vc.to_string())
            
    # Entities count
    print("\n--- Key Entity Uniques ---")
    for ec in ['Product No', 'Store', 'Supplier', 'Sales Channel', 'Department', 'Class', 'Sub Class', 'Brand']:
        if ec in df.columns:
            print(f"Unique {ec}: {df[ec].nunique():,}")

    return df

if __name__ == '__main__':
    inv_df = audit_file(INVENTORY_PATH, "INVENTORY DATASET")
    sales_df = audit_file(SALES_PATH, "SALES DATASET")
