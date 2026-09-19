import json
from io import BytesIO
from pathlib import Path
import tomllib

from api.app import app
from api.basket import _restored as restore_basket
from api.stock import _restored as restore_stock


ROOT = Path(__file__).resolve().parents[1]


def _blocking_issue(session: dict) -> str:
    return next(issue["issue_id"] for issue in session["issues"] if issue["blocks_planning"])


def test_supplier_basket_preview_is_stateless_and_exportable() -> None:
    _, initial = restore_basket("positive_moq_composition", [])
    service, resolved = restore_basket("positive_moq_composition", [_blocking_issue(initial)])

    assert resolved["decision"] is not None
    assert "supplier_id,supplier_name" in service.export(resolved["session_id"])


def test_stock_watch_preview_is_stateless_and_exportable() -> None:
    _, initial = restore_stock("balanced_action", [])
    service, resolved = restore_stock("balanced_action", [_blocking_issue(initial)])

    assert resolved["decision"] is not None
    assert "action,product_id" in service.export_order(resolved["session_id"])
    assert "product_id,product_name,lot_id" in service.export_risk(resolved["session_id"])


def test_vercel_preview_contract_keeps_demos_same_origin() -> None:
    config = json.loads((ROOT / "deployment" / "vercel-preview.json").read_text())

    project = tomllib.loads((ROOT / "deployment" / "vercel-preview.pyproject.toml").read_text())

    assert config["headers"]
    assert project["tool"]["vercel"]["entrypoint"] == "api.app:app"


def test_wsgi_entrypoint_exposes_the_same_origin_api() -> None:
    captured: dict = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(app({
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/basket/api/examples",
        "QUERY_STRING": "",
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(),
    }, start_response))

    assert captured["status"] == "200 OK"
    assert captured["headers"]["Content-Type"] == "application/json; charset=utf-8"
    assert len(json.loads(body)) == 3
