import pandas as pd
import json

with open("audit/reports/case_studies_data.json") as f:
    case_data = json.load(f)

for tag, c in case_data.items():
    print(f"\n========================================================")
    print(f"CASE STUDY: {tag}")
    print(f"Metadata: {c['metadata']}")
    print(f"\nInventory Intervals (first 10 of {len(c['inventory_raw'])}):")
    inv_df = pd.DataFrame(c['inventory_raw'])
    print(inv_df.head(10).to_string())
    
    print(f"\nSales Events (first 10 of {len(c['sales_raw'])}):")
    sales_df = pd.DataFrame(c['sales_raw'])
    print(sales_df.head(10).to_string())
    
    print(f"\nReconstructed Daily Events (Active Sales Days, first 10 of {len(c['daily_reconstructed'])}):")
    recon_df = pd.DataFrame(c['daily_reconstructed'])
    print(recon_df[['Date', 'qty_sold', 'sales_amount', 'qty_on_hand', 'stock_status', 'stock_unit_price']].head(10).to_string())
