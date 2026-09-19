"""Dependency-free local HTTP API and client application."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from .config import MAX_UPLOAD_BYTES, WEB_DIR
from .contracts import ImportContractError, ReconciliationBlocked
from .service import SupplierBasketService


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def make_handler(service: SupplierBasketService):
    """Bind one isolated service to a request handler class."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "SupplierBasketShowcase/1.0"

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            print(f"{self.address_string()} - {format % args}")

        def _headers(self, status: int, content_type: str, length: int, *, cache: str = "no-store", disposition: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", cache)
            for key, value in SECURITY_HEADERS.items():
                self.send_header(key, value)
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()

        def _json(self, status: int, payload: dict | list) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._json(status, {"error": message})

        def _body(self) -> dict:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ImportContractError("Content-Length is required")
            length = int(raw_length)
            if length < 0 or length > MAX_UPLOAD_BYTES + 100_000:
                raise ImportContractError("Request body exceeds the local showcase limit")
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ImportContractError("Request body must be valid UTF-8 JSON") from exc
            if not isinstance(payload, dict):
                raise ImportContractError("Request body must be a JSON object")
            return payload

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/basket")
            try:
                if path == "/api/health":
                    self._json(HTTPStatus.OK, {"status": "ready", "synthetic": True, "port": self.server.server_port})
                    return
                if path == "/api/examples":
                    self._json(HTTPStatus.OK, service.list_examples())
                    return
                if path.startswith("/api/sessions/") and path.endswith("/export"):
                    session_id = path.split("/")[3]
                    body = service.export(session_id).encode("utf-8")
                    self._headers(HTTPStatus.OK, "text/csv; charset=utf-8", len(body), disposition='attachment; filename="supplier-order-draft.csv"')
                    self.wfile.write(body)
                    return
                if path.startswith("/api/sessions/"):
                    session_id = path.split("/")[3]
                    self._json(HTTPStatus.OK, service.view(session_id))
                    return
                self._static(path)
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))
            except ReconciliationBlocked as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))
            except (ImportContractError, ValueError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/basket")
            try:
                payload = self._body()
                if path == "/api/sessions/example":
                    case_id = payload.get("case_id")
                    if not isinstance(case_id, str):
                        raise ImportContractError("case_id is required")
                    self._json(HTTPStatus.CREATED, service.create_example(case_id))
                    return
                if path == "/api/sessions/upload":
                    files = payload.get("files")
                    if not isinstance(files, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in files.items()):
                        raise ImportContractError("files must map exact CSV filenames to text")
                    self._json(HTTPStatus.CREATED, service.create_upload(files))
                    return
                if path.startswith("/api/sessions/") and path.endswith("/resolve"):
                    session_id = path.split("/")[3]
                    issue_id = payload.get("issue_id")
                    if not isinstance(issue_id, str):
                        raise ImportContractError("issue_id is required")
                    self._json(HTTPStatus.OK, service.resolve(session_id, issue_id))
                    return
                self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))
            except ReconciliationBlocked as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))
            except (ImportContractError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_DELETE(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/basket")
            try:
                if path.startswith("/api/sessions/") and len(path.split("/")) == 4:
                    service.delete(path.split("/")[3])
                    self._json(HTTPStatus.OK, {"deleted": True})
                    return
                self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))

        def _static(self, path: str) -> None:
            mapping = {
                "/": WEB_DIR / "index.html",
                "/index.html": WEB_DIR / "index.html",
                "/assets/style.css": WEB_DIR / "style.css",
                "/assets/app.js": WEB_DIR / "app.js",
            }
            target = mapping.get(path)
            if target is None or not target.is_file():
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            body = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type == "application/javascript":
                content_type += "; charset=utf-8"
            self._headers(HTTPStatus.OK, content_type, len(body), cache="no-cache")
            self.wfile.write(body)

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8765, service: SupplierBasketService | None = None) -> ThreadingHTTPServer:
    """Create the local server without starting its event loop."""
    return ThreadingHTTPServer((host, port), make_handler(service or SupplierBasketService()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Supplier Basket Review showcase")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Supplier Basket Review ready at http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
