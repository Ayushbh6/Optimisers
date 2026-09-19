"""Stateless Vercel adapter for the Supplier Basket Review showcase."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse

from src.supplier_basket.contracts import ImportContractError, ReconciliationBlocked
from src.supplier_basket.service import SupplierBasketService


def _restored(case_id: str, issue_ids: list[str]) -> tuple[SupplierBasketService, dict]:
    service = SupplierBasketService()
    session = service.create_example(case_id)
    for issue_id in issue_ids:
        session = service.resolve(session["session_id"], issue_id)
    return service, session


class handler(BaseHTTPRequestHandler):
    """Rebuild each tiny synthetic session per request so instance churn is safe."""

    def _headers(self, status: int, content_type: str, length: int, disposition: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()

    def _json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload).encode()
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 32_000:
            raise ImportContractError("Request is too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def _route(self) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        return "/" + query.get("route", [""])[0].lstrip("/"), query

    def do_GET(self) -> None:  # noqa: N802
        try:
            route, query = self._route()
            if route == "/api/health":
                self._json(HTTPStatus.OK, {"status": "ready", "synthetic": True, "product": "supplier-basket"})
                return
            if route == "/api/examples":
                self._json(HTTPStatus.OK, SupplierBasketService().list_examples())
                return
            if route.endswith("/export"):
                case_id = query.get("case_id", [""])[0]
                issue_ids = [item for item in query.get("issues", [""])[0].split(",") if item]
                service, session = _restored(case_id, issue_ids)
                body = service.export(session["session_id"]).encode()
                self._headers(HTTPStatus.OK, "text/csv; charset=utf-8", len(body), 'attachment; filename="supplier-order.csv"')
                self.wfile.write(body)
                return
            self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
        except (KeyError, ImportContractError, ReconciliationBlocked, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        try:
            route, _ = self._route()
            payload = self._body()
            if route != "/api/sessions/example" and not route.endswith("/resolve"):
                self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
                return
            case_id = payload.get("case_id", "")
            issue_ids = payload.get("resolved_issue_ids", [])
            if not isinstance(case_id, str) or not isinstance(issue_ids, list) or not all(isinstance(item, str) for item in issue_ids):
                raise ImportContractError("Invalid review request")
            _, session = _restored(case_id, issue_ids if route.endswith("/resolve") else [])
            self._json(HTTPStatus.CREATED if route == "/api/sessions/example" else HTTPStatus.OK, session)
        except (KeyError, ImportContractError, ReconciliationBlocked, ValueError, json.JSONDecodeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))

    def do_DELETE(self) -> None:  # noqa: N802
        self._json(HTTPStatus.OK, {"deleted": True})
