"""Independent arithmetic checks written without importing Stock Watch code."""

from decimal import Decimal
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
expected = {row["case_id"]: row for row in json.loads((ROOT / "expected-results.json").read_text())["cases"]}

# Balanced action: current 4 x 12 Oat cases; selected 2 x 12 Soup cases; one €10 delivery charge.
assert Decimal("4") * 12 * Decimal("1.50") + 10 == Decimal(expected["balanced_action"]["current_cash_eur"])
assert Decimal("2") * 12 * Decimal("2.00") + 10 == Decimal(expected["balanced_action"]["selected_cash_eur"])
assert 12 + 24 == 36  # Soup opening stock plus selected receipt covers three booked 12-unit lines.
assert 60 + 48 - 24 - 12 == expected["balanced_action"]["higher_current_expired_units"]
assert 60 - 24 - 12 == expected["balanced_action"]["higher_selected_expired_units"]

# Unsafe shelf life: eight days remain on 12 Oct, below the customer's 14-day requirement.
assert (20 - 12) < 14
assert Decimal("4") * 12 * Decimal("2.20") + 10 == Decimal(expected["unsafe_shelf_life"]["selected_cash_eur"])
assert 4 * 12 >= 36 + 12  # Incoming stock covers booked and higher-view demand; three cases do not.
assert 3 * 12 < 36 + 12

# Healthy control: opening 24 Tomato units cover booked demand; incoming 24 cover the higher view.
assert 24 + 24 == 12 + 12 + 24
assert Decimal("2") * 12 * Decimal("1.80") + 10 == Decimal(expected["healthy_control"]["selected_cash_eur"])

print(json.dumps({"status": "PASS", "cases_checked": 3, "method": "independent hand arithmetic"}, indent=2))
