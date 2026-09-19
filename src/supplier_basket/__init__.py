"""Supplier Basket Review showcase product.

The package is intentionally separate from the earlier distributor research
optimiser. It imports the frozen messy exports, reconciles an auditable ledger,
and lets a small exact physical replay judge whole-case basket alternatives.
"""

from .service import SupplierBasketService

__all__ = ["SupplierBasketService"]
