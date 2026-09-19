"""Small typed records shared by Stock Watch layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataIssue:
    issue_id: str
    classification: str
    title: str
    detail: str
    status: str
    affected_rows: tuple[str, ...]
    action_label: str | None = None

    @property
    def blocks(self) -> bool:
        return self.status == "pending" and self.classification in {"buyer_confirmation_required", "hard_blocker"}


@dataclass
class ImportedCase:
    case_id: str
    input_hash: str
    files: dict[str, str]
    rows: dict[str, list[dict[str, str]]]
    issues: list[DataIssue]
    approved_issue_ids: set[str] = field(default_factory=set)

    @property
    def blocked(self) -> bool:
        return any(issue.blocks for issue in self.issues)


@dataclass(frozen=True)
class ViewResult:
    view_id: str
    booked_units: int
    booked_on_time_units: int
    projected_units: int
    projected_fulfilled_units: int
    expired_units: int
    expired_cost_eur: str
    ending_stock_units: int
    ending_stock_eur: str
    run_outs: tuple[dict[str, Any], ...]
    daily_ledger: tuple[dict[str, Any], ...]
    accounting_errors: tuple[str, ...]


@dataclass(frozen=True)
class PlanResult:
    plan_id: str
    lines: tuple[dict[str, Any], ...]
    merchandise_eur: str
    delivery_charge_eur: str
    cash_eur: str
    views: tuple[ViewResult, ...]


@dataclass(frozen=True)
class DecisionResult:
    case_id: str
    input_hash: str
    decision_hash: str
    verdict: str
    current: PlanResult
    selected: PlanResult
    rejected: tuple[dict[str, Any], ...]
    actions: tuple[dict[str, Any], ...]
    at_risk_lots: tuple[dict[str, Any], ...]
    search_report: dict[str, Any]


class ImportContractError(ValueError):
    """Raw files do not follow the frozen example contract."""


class ReconciliationBlocked(ValueError):
    """A decision-critical issue still needs a buyer answer."""
