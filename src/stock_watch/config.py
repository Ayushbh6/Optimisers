"""Paths and frozen limits for the Stock Watch showcase."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "artifacts" / "stock-watch-showcase"
PHASE1_DIR = ARTIFACT_DIR / "phase-1"
RAW_DIR = ARTIFACT_DIR / "phase-2" / "raw"
WEB_DIR = Path(__file__).resolve().parent / "web"

EXPECTED_FILES = (
    "products.csv",
    "product_aliases.csv",
    "stock_lots.csv",
    "customer_orders.csv",
    "purchases.csv",
    "supplier_terms.csv",
    "demand_views.csv",
)

CASE_LABELS = {
    "balanced_action": "Buy what is needed",
    "unsafe_shelf_life": "Protect the customer order",
    "healthy_control": "Leave a healthy plan alone",
}

REQUIRED_VIEWS = ("lower", "nominal", "higher", "irregular")
MAX_CANDIDATES = 25
MAX_SESSIONS = 32
MAX_FILE_BYTES = 1_000_000
MAX_UPLOAD_BYTES = 5_000_000
