"""Single dependency-free WSGI entrypoint for the complete Axis preview."""

from http import HTTPStatus
import json
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote

from api.basket import _restored as restore_basket
from api.stock import _restored as restore_stock
from src.stock_watch.contracts import ImportContractError as StockImportError
from src.stock_watch.contracts import ReconciliationBlocked as StockBlocked
from src.supplier_basket.contracts import ImportContractError as BasketImportError
from src.supplier_basket.contracts import ReconciliationBlocked as BasketBlocked
from src.supplier_basket.service import SupplierBasketService
from src.stock_watch.service import StockWatchService


PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
API_ERRORS = (KeyError, ValueError, BasketImportError, BasketBlocked, StockImportError, StockBlocked)


def _response(start_response, status: HTTPStatus, body: bytes, content_type: str, *, disposition: str | None = None, cache: str = "no-store"):
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", cache),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ]
    if disposition:
        headers.append(("Content-Disposition", disposition))
    start_response(f"{status.value} {status.phrase}", headers)
    return [body]


def _json(start_response, status: HTTPStatus, payload: dict | list):
    body = json.dumps(payload, separators=(",", ":")).encode()
    return _response(start_response, status, body, "application/json; charset=utf-8")


def _issue_ids(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Invalid issue list")
    return value


def _payload(environ) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > 32_000:
        raise ValueError("Request is too large")
    value = json.loads(environ["wsgi.input"].read(length) or b"{}")
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _not_found(start_response):
    target = PUBLIC_DIR / "404.html"
    if target.is_file():
        return _response(start_response, HTTPStatus.NOT_FOUND, target.read_bytes(), "text/html; charset=utf-8", cache="no-cache")
    return _json(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found"})


def _serve_static(start_response, path: str):
    requested = unquote(path or "/")
    relative = requested.lstrip("/") or "index.html"
    if requested.endswith("/"):
        relative += "index.html"
    target = (PUBLIC_DIR / relative).resolve()
    try:
        target.relative_to(PUBLIC_DIR.resolve())
    except ValueError:
        return _not_found(start_response)
    if not target.is_file():
        return _not_found(start_response)
    body = target.read_bytes()
    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
        content_type += "; charset=utf-8"
    cache = "public, max-age=31536000, immutable" if "/_astro/" in target.as_posix() else "no-cache"
    return _response(start_response, HTTPStatus.OK, body, content_type, cache=cache)


def app(environ, start_response):
    """Serve stateless showcase APIs; Vercel serves files in public before WSGI."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    query = parse_qs(environ.get("QUERY_STRING", ""))
    path = query.get("_axis_path", [environ.get("PATH_INFO", "/")])[0].rstrip("/")
    try:
        if method == "GET":
            if path == "/api/basket/api/health":
                return _json(start_response, HTTPStatus.OK, {"status": "ready", "synthetic": True, "product": "supplier-basket"})
            if path == "/api/stock/api/health":
                return _json(start_response, HTTPStatus.OK, {"status": "ready", "synthetic": True, "product": "stock-watch"})
            if path == "/api/basket/api/examples":
                return _json(start_response, HTTPStatus.OK, SupplierBasketService().list_examples())
            if path == "/api/stock/api/examples":
                return _json(start_response, HTTPStatus.OK, StockWatchService().examples())
            if path.startswith("/api/basket/api/sessions/") and path.endswith("/export"):
                service, session = restore_basket(query.get("case_id", [""])[0], [item for item in query.get("issues", [""])[0].split(",") if item])
                body = service.export(session["session_id"]).encode()
                return _response(start_response, HTTPStatus.OK, body, "text/csv; charset=utf-8", disposition='attachment; filename="supplier-order.csv"')
            if path.startswith("/api/stock/api/sessions/") and (path.endswith("/export-order") or path.endswith("/export-risk")):
                service, session = restore_stock(query.get("case_id", [""])[0], [item for item in query.get("issues", [""])[0].split(",") if item])
                if path.endswith("/export-order"):
                    body, filename = service.export_order(session["session_id"]).encode(), "stock-watch-order.csv"
                else:
                    body, filename = service.export_risk(session["session_id"]).encode(), "stock-watch-risk-list.csv"
                return _response(start_response, HTTPStatus.OK, body, "text/csv; charset=utf-8", disposition=f'attachment; filename="{filename}"')
            if path.startswith("/api/"):
                return _json(start_response, HTTPStatus.NOT_FOUND, {"error": "Unknown API route"})
            return _serve_static(start_response, environ.get("PATH_INFO", "/"))

        if method == "POST":
            payload = _payload(environ)
            case_id = payload.get("case_id", "")
            if not isinstance(case_id, str):
                raise ValueError("Invalid case")
            resolved = _issue_ids(payload.get("resolved_issue_ids", []))
            if path == "/api/basket/api/sessions/example":
                _, session = restore_basket(case_id, [])
                return _json(start_response, HTTPStatus.CREATED, session)
            if path.startswith("/api/basket/api/sessions/") and path.endswith("/resolve"):
                _, session = restore_basket(case_id, resolved)
                return _json(start_response, HTTPStatus.OK, session)
            if path == "/api/stock/api/sessions/example":
                _, session = restore_stock(case_id, [])
                return _json(start_response, HTTPStatus.CREATED, session)
            if path.startswith("/api/stock/api/sessions/") and path.endswith("/resolve"):
                _, session = restore_stock(case_id, resolved)
                return _json(start_response, HTTPStatus.OK, session)
            return _json(start_response, HTTPStatus.NOT_FOUND, {"error": "Unknown API route"})

        if method == "DELETE":
            return _json(start_response, HTTPStatus.OK, {"deleted": True})
        return _json(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"})
    except (json.JSONDecodeError, *API_ERRORS) as exc:
        return _json(start_response, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
