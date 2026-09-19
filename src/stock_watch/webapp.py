"""Dependency-free local API and static application for Stock Watch."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from urllib.parse import urlparse

from .config import WEB_DIR
from .contracts import ImportContractError, ReconciliationBlocked
from .service import StockWatchService


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cross-Origin-Resource-Policy": "same-origin",
}


def make_handler(service: StockWatchService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "StockWatchShowcase/1.0"

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            print(f"{self.address_string()} - {format % args}")

        def _headers(self, status: int, content_type: str, length: int, disposition: str | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            if disposition:
                self.send_header("Content-Disposition", disposition)
            for key, value in SECURITY_HEADERS.items():
                self.send_header(key, value)
            self.end_headers()

        def _json(self, status: int, payload: dict | list) -> None:
            body = json.dumps(payload).encode()
            self._headers(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._json(status, {"error": message})

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ImportContractError("Request is too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/stock")
            try:
                if path == "/api/health":
                    self._json(HTTPStatus.OK, {"status": "ready", "synthetic": True, "product": "stock-watch"})
                elif path == "/api/examples":
                    self._json(HTTPStatus.OK, service.examples())
                elif path.startswith("/api/sessions/") and path.endswith("/export-order"):
                    body = service.export_order(path.split("/")[3]).encode()
                    self._headers(HTTPStatus.OK, "text/csv; charset=utf-8", len(body), 'attachment; filename="stock-watch-order.csv"')
                    self.wfile.write(body)
                elif path.startswith("/api/sessions/") and path.endswith("/export-risk"):
                    body = service.export_risk(path.split("/")[3]).encode()
                    self._headers(HTTPStatus.OK, "text/csv; charset=utf-8", len(body), 'attachment; filename="stock-watch-risk-list.csv"')
                    self.wfile.write(body)
                elif path.startswith("/api/sessions/"):
                    self._json(HTTPStatus.OK, service.view(path.split("/")[3]))
                else:
                    self._static(path)
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))
            except (ImportContractError, ReconciliationBlocked, ValueError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/stock")
            try:
                payload = self._body()
                if path == "/api/sessions/example":
                    self._json(HTTPStatus.CREATED, service.create_example(payload.get("case_id", "")))
                elif path.startswith("/api/sessions/") and path.endswith("/resolve"):
                    self._json(HTTPStatus.OK, service.resolve(path.split("/")[3], payload.get("issue_id", "")))
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))
            except (ImportContractError, ReconciliationBlocked, ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_DELETE(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.removeprefix("/api/stock")
            try:
                if path.startswith("/api/sessions/"):
                    service.delete(path.split("/")[3])
                    self._json(HTTPStatus.OK, {"deleted": True})
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Unknown API route")
            except KeyError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))

        def _static(self, path: str) -> None:
            mapping = {"/": WEB_DIR / "index.html", "/index.html": WEB_DIR / "index.html", "/assets/style.css": WEB_DIR / "style.css", "/assets/app.js": WEB_DIR / "app.js"}
            target = mapping.get(path)
            if target is None or not target.is_file():
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            body = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type == "application/javascript":
                content_type += "; charset=utf-8"
            self._headers(HTTPStatus.OK, content_type, len(body))
            self.wfile.write(body)

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8766, service: StockWatchService | None = None) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(service or StockWatchService()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Ledgerline Stock Watch")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Ledgerline Stock Watch ready at http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
