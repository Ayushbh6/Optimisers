"""Typed public planning inputs; quantities are units and money is euro cents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from hashlib import sha256
import json


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    case: int
    volume_ml: int
    shelf_days: int


@dataclass(frozen=True)
class Supplier:
    id: str
    weekday: int
    lead_days: int
    minimum_cents: int
    fee_cents: int


@dataclass(frozen=True)
class Term:
    supplier: str
    product: str
    cost: int
    minimum: int
    start: date
    end: date | None = None


@dataclass(frozen=True)
class Customer:
    id: str
    partial: bool
    late_days: int
    freshness_days: int


@dataclass
class Lot:
    id: str
    product: str
    received: date
    expiry: date
    cost: int
    units: int


@dataclass
class Demand:
    id: str
    product: str
    customer: str
    created: date
    due: date
    units: int
    shipped: int = 0
    cancelled: int = 0
    on_time: int = 0
    estimated: bool = False

    @property
    def remaining(self) -> int:
        return self.units - self.shipped - self.cancelled


@dataclass
class Incoming:
    id: str
    order: str
    supplier: str
    product: str
    placed: date
    expected: date | None
    units: int
    cost: int
    received: int = 0
    cancelled: int = 0

    @property
    def remaining(self) -> int:
        return self.units - self.received - self.cancelled


@dataclass(frozen=True)
class Purchase:
    day: date
    supplier: str
    product: str
    units: int


@dataclass
class PlanningSnapshot:
    """Only released operational knowledge, never hidden delivery schedules."""
    day: date
    products: dict[str, Product]
    suppliers: dict[str, Supplier]
    customers: dict[str, Customer]
    terms: list[Term]
    lots: dict[str, Lot]
    demand: dict[str, Demand]
    incoming: dict[str, Incoming]
    budget_cents: int
    capacity_ml: int
    week_spend: int = 0
    synthetic: bool = True
    notices: list[dict] = field(default_factory=list)
    promotions: list[dict] = field(default_factory=list)
    request_history_start: date | None = None

    def term(self, supplier: str, product: str, day: date | None = None) -> Term:
        """Resolve exactly one commercial term effective on the purchasing date."""
        at = day or self.day
        found = [t for t in self.terms if t.supplier == supplier and t.product == product
                 and t.start <= at and (t.end is None or at <= t.end)]
        if len(found) != 1:
            raise ValueError(f"Expected one active cost/term: {supplier}/{product} on {at}")
        return found[0]

    def identity(self) -> str:
        """Hash public state for reproducibility and stale-result detection."""
        from dataclasses import asdict
        return sha256(json.dumps(asdict(self), default=str, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class PlannerSettings:
    horizon_days: int = 28
    safety_workdays: int = 0
    forecast_method: str = "mean4"
    incoming_freshness_days: int = 60
    delay_workdays: int = 0
    demand_multiplier: float = 1.0
    solve_seconds: float = 3.0


@dataclass
class ForecastBundle:
    method: str
    daily: dict[tuple[str, date], float]
    errors: dict[str, float]
    warnings: list[str]
    pattern: list[Demand] | None = None
    provenance: dict = field(default_factory=dict)


@dataclass
class PlanRequest:
    snapshot: PlanningSnapshot
    settings: PlannerSettings = field(default_factory=PlannerSettings)
    locks: dict[str, int] = field(default_factory=dict)
    excluded: tuple[str, ...] = ()

    def identity(self) -> str:
        """Include all buyer assumptions and edits, not just source records."""
        from dataclasses import asdict
        value = dict(snapshot=self.snapshot.identity(), settings=asdict(self.settings),
                     locks=self.locks, excluded=sorted(self.excluded))
        return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass
class Alternative:
    name: str
    purchases: list[Purchase]
    metrics: dict
    status: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class PlanResult:
    input_hash: str
    alternatives: list[Alternative]
    recommended: str
    warnings: list[str]
    version: str = "replenishment-v5-adaptive-discrete-physical-search"
    sensitivity: dict = field(default_factory=dict)
