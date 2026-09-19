"""Isolated in-memory sessions for the local Stock Watch showcase."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
import uuid

from .config import CASE_LABELS, MAX_SESSIONS
from .contracts import ImportedCase, ReconciliationBlocked
from .engine import optimise
from .importer import approve_issue, load_example, reconcile
from .reporting import decision_payload, risk_csv, supplier_csv


@dataclass
class Session:
    imported: ImportedCase
    position: dict | None = None
    decision: object | None = None


class StockWatchService:
    """Own bounded local sessions and expose one stable application contract."""

    def __init__(self) -> None:
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._lock = RLock()

    def examples(self) -> list[dict[str, str]]:
        return [{"case_id": key, "label": value} for key, value in CASE_LABELS.items()]

    def create_example(self, case_id: str) -> dict:
        imported = load_example(case_id)
        with self._lock:
            while len(self._sessions) >= MAX_SESSIONS:
                self._sessions.popitem(last=False)
            session_id = uuid.uuid4().hex
            self._sessions[session_id] = Session(imported)
        return self._calculate(session_id)

    def resolve(self, session_id: str, issue_id: str) -> dict:
        with self._lock:
            session = self._get(session_id)
            session.imported = approve_issue(session.imported, issue_id)
            session.position = None
            session.decision = None
        return self._calculate(session_id)

    def view(self, session_id: str) -> dict:
        return self._calculate(session_id)

    def export_order(self, session_id: str) -> str:
        session = self._get(session_id)
        if session.decision is None:
            raise ReconciliationBlocked("Resolve the records before exporting")
        return supplier_csv(session.decision)

    def export_risk(self, session_id: str) -> str:
        session = self._get(session_id)
        if session.decision is None:
            raise ReconciliationBlocked("Resolve the records before exporting")
        return risk_csv(session.decision)

    def delete(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("Unknown session")
            del self._sessions[session_id]

    def _get(self, session_id: str) -> Session:
        with self._lock:
            try:
                session = self._sessions[session_id]
            except KeyError as exc:
                raise KeyError("Unknown session") from exc
            self._sessions.move_to_end(session_id)
            return session

    def _calculate(self, session_id: str) -> dict:
        session = self._get(session_id)
        if not session.imported.blocked and session.decision is None:
            session.position = reconcile(session.imported)
            session.decision = optimise(session.position)
        return {
            "session_id": session_id, "case_id": session.imported.case_id,
            "label": CASE_LABELS[session.imported.case_id], "input_hash": session.imported.input_hash,
            "blocked": session.imported.blocked,
            "source_row_count": sum(len(rows) for rows in session.imported.rows.values()),
            "issues": [
                {
                    "issue_id": issue.issue_id, "classification": issue.classification, "title": issue.title,
                    "detail": issue.detail, "status": issue.status, "affected_rows": list(issue.affected_rows),
                    "action_label": issue.action_label, "blocks_planning": issue.blocks,
                }
                for issue in session.imported.issues
            ],
            "decision": decision_payload(session.decision) if session.decision else None,
        }
