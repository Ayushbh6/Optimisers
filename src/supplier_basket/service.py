"""Thread-safe application service for import-to-export showcase sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any
from uuid import uuid4

from .config import CASE_LABELS, MAX_SESSIONS
from .contracts import DecisionResult, ImportedCase, ImportContractError, ReconciliationBlocked
from .importer import approve_issue, import_files, load_example
from .optimizer import optimise
from .reconciliation import stable_reconcile
from .reporting import decision_payload, supplier_csv


@dataclass
class SessionState:
    session_id: str
    imported: ImportedCase
    ledger: dict[str, Any] | None = None
    decision: DecisionResult | None = None


class SupplierBasketService:
    """Own isolated local sessions and reject stale downstream decisions."""

    def __init__(self, max_sessions: int = MAX_SESSIONS):
        self._max_sessions = max_sessions
        self._sessions: dict[str, SessionState] = {}
        self._lock = RLock()

    def list_examples(self) -> list[dict[str, str]]:
        """Return the three labelled examples in stable order."""
        return [{"case_id": case_id, "label": label} for case_id, label in CASE_LABELS.items()]

    def _build(self, imported: ImportedCase) -> SessionState:
        state = SessionState(uuid4().hex, imported)
        self._refresh(state)
        return state

    def _refresh(self, state: SessionState) -> None:
        state.ledger = None
        state.decision = None
        if state.imported.blocked:
            return
        state.ledger = stable_reconcile(state.imported)
        state.decision = optimise(state.ledger)

    def _store(self, state: SessionState) -> SessionState:
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                oldest = next(iter(self._sessions))
                del self._sessions[oldest]
            self._sessions[state.session_id] = state
        return state

    def create_example(self, case_id: str) -> dict[str, Any]:
        """Create a fresh session from bundled bytes without auto-approving buyer actions."""
        return self.view(self._store(self._build(load_example(case_id))).session_id)

    def create_upload(self, files: dict[str, str]) -> dict[str, Any]:
        """Create a session from user-supplied CSV strings."""
        return self.view(self._store(self._build(import_files(files))).session_id)

    def _get(self, session_id: str) -> SessionState:
        with self._lock:
            state = self._sessions.get(session_id)
        if state is None:
            raise KeyError("Unknown or expired session")
        return state

    def resolve(self, session_id: str, issue_id: str) -> dict[str, Any]:
        """Apply one explicit evidence-backed action and invalidate stale results."""
        state = self._get(session_id)
        old_hash = state.imported.input_hash
        state.imported = approve_issue(state.imported, issue_id)
        if state.imported.input_hash != old_hash:
            raise AssertionError("Approving an issue must not mutate source bytes")
        self._refresh(state)
        return self.view(session_id)

    def view(self, session_id: str) -> dict[str, Any]:
        """Return a JSON-ready session view without leaking raw rows."""
        state = self._get(session_id)
        if state.decision and state.decision.input_hash != state.imported.input_hash:
            raise AssertionError("Stale decision does not match current source hash")
        return {
            "session_id": state.session_id,
            "case_id": state.imported.case_id,
            "label": CASE_LABELS[state.imported.case_id],
            "input_hash": state.imported.input_hash,
            "blocked": state.imported.blocked,
            "source_row_count": sum(len(rows) for rows in state.imported.rows.values()),
            "issues": [
                {
                    **asdict(issue),
                    "blocks_planning": issue.blocks_planning,
                }
                for issue in state.imported.issues
            ],
            "ledger": state.ledger,
            "decision": decision_payload(state.decision) if state.decision else None,
        }

    def export(self, session_id: str) -> str:
        """Export the current selected basket only when the session is ready."""
        state = self._get(session_id)
        if state.decision is None:
            raise ReconciliationBlocked("Resolve all blocking issues before export")
        if state.decision.input_hash != state.imported.input_hash:
            raise ImportContractError("Source data changed; rerun the decision before export")
        return supplier_csv(state.decision)

    def delete(self, session_id: str) -> None:
        """Delete one session and all of its in-memory source data."""
        with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise KeyError("Unknown or expired session")
