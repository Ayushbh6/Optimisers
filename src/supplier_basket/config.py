"""Frozen showcase paths and operational limits."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE1_DIR = REPO_ROOT / "artifacts" / "supplier-basket-showcase" / "phase-1"
PHASE2_DIR = REPO_ROOT / "artifacts" / "supplier-basket-showcase" / "phase-2"
RAW_DIR = PHASE2_DIR / "raw"
ISSUE_REGISTER_PATH = PHASE2_DIR / "issue-register.json"
WEB_DIR = Path(__file__).resolve().parent / "web"

MAX_FILE_BYTES = 1_000_000
MAX_UPLOAD_BYTES = 5_000_000
MAX_SESSIONS = 32

EXPECTED_FILES = (
    "products.csv",
    "supplier_terms.csv",
    "stock_snapshot.csv",
    "customer_orders.csv",
    "purchase_orders.csv",
    "receipts.csv",
    "resolutions.csv",
)

CASE_LABELS = {
    "positive_moq_composition": "Safe minimum-order composition",
    "unsafe_cheaper_delivery_loss": "Cheaper basket with delivery risk",
    "no_change_control": "Keep the buyer order",
}

CASE_PREFIXES = {
    "POS": "positive_moq_composition",
    "UNS": "unsafe_cheaper_delivery_loss",
    "CTL": "no_change_control",
}
