"""One incremental estimator shared by historical reconstruction and shop replay."""
from __future__ import annotations

import numpy as np
import pandas as pd


class DemandState:
    """Learn only from fully available days, after estimating the current day.

    Group keys come from metadata already known on the observation date. Missing
    categories never pool together. Arrays keep the full-data replay practical.
    """

    def __init__(self, pairs: pd.MultiIndex | list, minimum: int = 7) -> None:
        self.pairs = pd.MultiIndex.from_tuples(list(pairs), names=['Product No', 'Store'])
        self.products = self.pairs.get_level_values(0).to_numpy()
        self.stores = self.pairs.get_level_values(1).to_numpy()
        self.minimum = minimum
        self.tables = [{} for _ in range(4)]

    def step(self, purchases: np.ndarray, known: np.ndarray, available: np.ndarray, categories: list, *, estimated_exposure: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return estimates using yesterday's rates, then add today's donors."""
        purchases = np.asarray(purchases, float)
        known, available = np.asarray(known, bool), np.asarray(available, bool)
        n = len(purchases)
        estimate = purchases.copy()
        fallback = np.where(known, 'recorded_purchase', 'insufficient_stock_evidence').astype(object)
        unresolved = known & ~available
        fallback[unresolved] = 'insufficient_prior_rate'
        estimated_exposure = np.zeros(n, bool) if estimated_exposure is None else np.asarray(estimated_exposure, bool)
        donor_counts = np.zeros(n, np.int64)
        estimated_counts = np.zeros(n, np.int64)
        categories = list(categories)
        keys = [list(self.pairs), list(self.products),
                [(category, store) if category is not None else None for category, store in zip(categories, self.stores)],
                categories]
        labels = ['sku_store_prior_mean', 'sku_global_prior_mean', 'subcategory_store_prior_mean', 'subcategory_global_prior_mean']
        # Freeze all four levels until all current-day estimates have been made.
        encoded = []
        for table, group_keys, label in zip(self.tables, keys, labels):
            codes, unique = pd.factorize(pd.Series(group_keys, dtype=object), sort=False)
            values = np.array([table.get(key, (0., 0., 0.)) for key in unique], float).reshape(-1, 3)
            valid = codes >= 0
            count = np.zeros(n); total = np.zeros(n); assumed = np.zeros(n)
            count[valid] = values[codes[valid], 1]
            total[valid] = values[codes[valid], 0]
            assumed[valid] = values[codes[valid], 2]
            take = unresolved & (count >= self.minimum)
            estimate[take] = np.maximum(purchases[take], total[take] / count[take])
            fallback[take] = label
            donor_counts[take] = count[take].astype(int)
            estimated_counts[take] = assumed[take].astype(int)
            unresolved[take] = False
            encoded.append((table, codes, unique, values))
        for table, codes, unique, values in encoded:
            mask = known & available & (codes >= 0)
            if not mask.any():
                continue
            values[:, 0] += np.bincount(codes[mask], weights=purchases[mask], minlength=len(unique))
            values[:, 1] += np.bincount(codes[mask], minlength=len(unique))
            values[:, 2] += np.bincount(codes[mask], weights=estimated_exposure[mask], minlength=len(unique))
            for key, value in zip(unique, values):
                table[key] = tuple(value)
        return estimate, fallback, donor_counts, estimated_counts
