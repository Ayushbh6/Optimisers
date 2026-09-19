"""Typed contracts shared by import, reconciliation, replay and web layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportIssue:
    """One visible data-quality decision and its current lifecycle state."""

    issue_id: str
    classification: str
    title: str
    detail: str
    status: str
    affected_rows: tuple[str, ...]
    resolution_id: str | None = None
    action_label: str | None = None

    @property
    def blocks_planning(self) -> bool:
        return self.status == "pending" and self.classification in {
            "buyer_confirmation_required",
            "hard_blocker",
        }


@dataclass
class ImportedCase:
    """Immutable raw rows plus issue state for one upload session."""

    case_id: str
    input_hash: str
    files: dict[str, str]
    rows: dict[str, list[dict[str, str]]]
    issues: list[ImportIssue]
    approved_issue_ids: set[str] = field(default_factory=set)

    @property
    def blocked(self) -> bool:
        return any(issue.blocks_planning for issue in self.issues)


@dataclass(frozen=True)
class ReplayResult:
    """Exact 28-day physical outcome for one supplier basket."""

    basket_id: str
    lines: tuple[dict[str, Any], ...]
    merchandise_eur: str
    delivery_charge_eur: str
    immediate_cash_eur: str
    on_time_units: int
    complete_lines: int
    booked_units: int
    booked_lines: int
    expired_units: int
    expired_cost_eur: str
    average_daily_exposure_eur: str
    sum_28_daily_exposure_eur: str
    ending_stock_eur: str
    ending_incoming_eur: str
    ending_undelivered_commitments_eur: str
    ending_stock_plus_commitments_eur: str
    delivery_failures: tuple[dict[str, Any], ...]
    daily_ledger: tuple[dict[str, Any], ...]
    accounting_errors: tuple[str, ...]


@dataclass(frozen=True)
class CandidateResult:
    """Preflight and replay evidence for one bounded alternative."""

    candidate_id: str
    generation_reason: str
    basket: tuple[dict[str, Any], ...]
    preflight_errors: tuple[str, ...]
    replay: ReplayResult | None
    decision_status: str
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class DecisionResult:
    """Complete deterministic recommendation and explanation payload."""

    case_id: str
    input_hash: str
    decision_hash: str
    verdict: str
    buyer: ReplayResult
    selected: ReplayResult
    candidates: tuple[CandidateResult, ...]
    product_changes: tuple[dict[str, Any], ...]
    summary: str
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    search_report: dict[str, Any]


class ImportContractError(ValueError):
    """Raised when source files violate the declared import contract."""


class ReconciliationBlocked(ValueError):
    """Raised when a decision-critical issue has not been resolved."""
