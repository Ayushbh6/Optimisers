"""Versioned, explicit assumptions for distributor demonstration data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = "distributor-demo-v2"
SCENARIO_FAMILIES = (
    "ordinary",
    "restricted_spending",
    "supplier_disruption",
    "demand_changes",
    "ageing_stock",
    "ample_stock",
)
DEVELOPMENT_SEEDS = (1101, 2202, 3303)
EVALUATION_SEEDS = (4404, 5505, 6606, 7707, 8808)

# Fixed v2 recipe: these are scenario-design choices, not industry estimates.
GENERATION_RULES = {
    "order_probability": {"fast": 0.055, "moderate": 0.025, "intermittent": 0.008},
    "customer_size_multiplier": {"small": 0.75, "medium": 1.0, "large": 1.4},
    "positive_quantity_range": {"fast": [3, 18], "moderate": [2, 12], "intermittent": [1, 8]},
    "preferred_products_per_customer": 12,
    "weekday_probability_multiplier": [1.2, 1.2, 0.9, 0.9, 0.9],
    "category_day_multiplier_range": [0.82, 1.18],
    "customer_due_workdays": [1, 3],
    "promotion_quantity_multiplier": 1.75,
    "unexpected_quantity_multiplier": 1.9,
    "ordinary_delay_probability": 0.04,
    "short_delivery_completion_workdays": 2,
    "receipt_age_days_at_expected_arrival": 14,
    "history_average_calendar_days": 28,
    "history_review_calendar_days": 7,
    "ample_stock_extra_cover_calendar_days": 28,
    "ample_stock_campaign_final_weeks": 6,
    "opening_daily_units_by_class": {"fast": 9, "moderate": 4, "intermittent": 1},
    "opening_cover_weeks": 2.2,
    "ample_opening_cover_weeks": 5,
    "ageing_opening_slow_stock_multiplier": 3,
    "supply_tail_calendar_days": 30,
}


@dataclass(frozen=True)
class DemoConfig:
    """All fixed choices required to reproduce one scenario."""

    scenario_family: str = "supplier_disruption"
    seed: int = 1101
    history_start: str = "2025-01-06"
    history_weeks: int = 26
    future_weeks: int = 8
    product_count: int = 30
    supplier_count: int = 4
    customer_count: int = 20
    warehouse_capacity_millilitres: int = 5_000_000
    weekly_order_budget_cents: int = 220_000
    restricted_weekly_order_budget_cents: int = 95_000
    schema_version: str = SCHEMA_VERSION
    synthetic_label: str = "SYNTHETIC DEMONSTRATION DATA — NOT CLIENT RECORDS"

    @property
    def history_end(self) -> date:
        return date.fromisoformat(self.history_start) + timedelta(days=self.history_weeks * 7 - 1)

    @property
    def future_start(self) -> date:
        return self.history_end + timedelta(days=1)

    @property
    def future_end(self) -> date:
        return self.future_start + timedelta(days=self.future_weeks * 7 - 1)

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Configuration schema version does not match implementation")
        if date.fromisoformat(self.history_start).weekday() != 0:
            raise ValueError("History must start on a Monday")
        if self.scenario_family not in SCENARIO_FAMILIES:
            raise ValueError(f"Unknown scenario family: {self.scenario_family}")
        if self.seed not in DEVELOPMENTS_AND_EVALUATION:
            raise ValueError("Seed must be declared as development or reserved evaluation")
        if (self.product_count, self.supplier_count, self.customer_count) != (30, 4, 20):
            raise ValueError("Version 1 requires exactly 30 products, 4 suppliers and 20 customers")
        if self.history_weeks != 26 or self.future_weeks != 8:
            raise ValueError("Version 1 requires 26 historical weeks and 8 future weeks")
        if self.weekly_order_budget_cents <= 0 or self.restricted_weekly_order_budget_cents <= 0 or self.warehouse_capacity_millilitres <= 0:
            raise ValueError("Budget and capacity must be positive")

    @property
    def effective_budget_cents(self) -> int:
        """Declared weekly new-order allowance for this scenario."""
        return self.restricted_weekly_order_budget_cents if self.scenario_family == "restricted_spending" else self.weekly_order_budget_cents

    def public_dict(self) -> dict:
        """Return the evaluator-only regeneration configuration, never planner input."""
        values = asdict(self)
        values.update(
            {
                "history_end": self.history_end.isoformat(),
                "future_start": self.future_start.isoformat(),
                "future_end": self.future_end.isoformat(),
                "seed_class": "development" if self.seed in DEVELOPMENT_SEEDS else "reserved_evaluation",
                "generation_rules": GENERATION_RULES,
            }
        )
        return values

    def identity(self) -> str:
        """Return a stable hash for the complete configuration."""
        payload = json.dumps(self.public_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


DEVELOPMENTS_AND_EVALUATION = DEVELOPMENT_SEEDS + EVALUATION_SEEDS


def default_config(family: str = "supplier_disruption", seed: int = 1101) -> DemoConfig:
    """Create and validate the agreed version-one scenario configuration."""
    config = DemoConfig(scenario_family=family, seed=seed)
    config.validate()
    return config


def write_config(config: DemoConfig, path: Path) -> None:
    """Write a human-readable regeneration contract."""
    path.write_text(json.dumps(config.public_dict(), indent=2, sort_keys=True) + "\n")


ASSUMPTIONS = (
    ("purchase_cost", "€0.50–€8.00 per sale unit", "Illustrative design range", "Changes cash needed for an order."),
    ("case_size", "6, 12 or 24 units", "Illustrative design choices", "Controls order rounding."),
    ("minimum_order", "1–4 cases per product", "Illustrative design range", "Can force excess units."),
    ("supplier_minimum", "€0, €100 or €250", "Illustrative design choices", "Can prevent a small supplier order."),
    ("lead_time", "2–7 working days", "Illustrative design range", "Controls how early stock is needed."),
    ("delivery_charge", "€0–€30 per supplier order", "Illustrative design range", "Makes fragmented orders visible."),
    ("shelf_life", "90–365 calendar days", "Illustrative packaged-food range", "Controls expiry exposure."),
    ("customer_freshness", "14, 30 or 60 days", "Illustrative customer terms", "Can make a lot ineligible before expiry."),
    ("late_delivery", "0, 2 or 5 working days", "Illustrative customer terms", "Controls cancellation timing."),
)
