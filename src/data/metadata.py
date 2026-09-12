"""Dated, pair-local product facts; absent categories remain absent."""
from __future__ import annotations
import pandas as pd

FIELDS = ['Product Division', 'Product Category', 'Product Subcategory', 'Product Segment']


def metadata_events(inventory: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """Retain facts when first observed in either ledger, never future-fill them."""
    frames = []
    for data, date_col in ((sales, 'Transaction Date'), (inventory, 'Start Date')):
        fields = [field for field in FIELDS if field in data]
        if fields:
            frames.append(data[['Product No', 'Store', date_col] + fields].rename(columns={date_col: 'effective_date'}))
    result = pd.concat(frames, ignore_index=True)
    result['effective_date'] = pd.to_datetime(result['effective_date'])
    result = result.sort_values('effective_date', kind='stable').drop_duplicates(['Product No', 'Store', 'effective_date'], keep='last')
    for field in FIELDS:
        if field not in result:
            result[field] = None
        result[field] = result.groupby(['Product No', 'Store'])[field].ffill()
    return result.reset_index(drop=True)


def resolve_metadata(hierarchy: pd.DataFrame, cutoff: str | pd.Timestamp, pairs: pd.MultiIndex | list | None = None) -> pd.DataFrame:
    """Resolve only events through cutoff; static fixtures are already-known facts."""
    data = hierarchy.copy()
    date_col = next((c for c in ('effective_date', 'Start Date', 'date') if c in data), None)
    keys = ['Product No', 'Store'] if 'Store' in data else ['Product No']
    if date_col:
        data = data[pd.to_datetime(data[date_col]) <= pd.Timestamp(cutoff)].sort_values(date_col, kind='stable')
    data = data.drop_duplicates(keys, keep='last')
    for field in FIELDS:
        if field not in data:
            data[field] = None
    data = data[keys + FIELDS]
    if pairs is not None:
        base = pd.DataFrame(list(pairs), columns=['Product No', 'Store'])
        data = base.merge(data, on=keys, how='left', validate='many_to_one')
    return data


def category_keys(metadata: pd.DataFrame) -> list[tuple | None]:
    """Division is included so identically named subcategories cannot mix."""
    return [(d, c) if pd.notna(d) and pd.notna(c) else None
            for d, c in zip(metadata['Product Division'], metadata['Product Subcategory'])]
