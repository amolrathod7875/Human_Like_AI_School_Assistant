from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app


class _Item(BaseModel):
    name: str


def _build_app_with_validation_route() -> FastAPI:
    app = create_app()

    @app.post("/api/v1/_test_validation")
    async def create_item(item: _Item):  # pragma: no cover - test only
        return item

    return app


def test_validation_error_is_standardized():
    app = _build_app_with_validation_route()
    with TestClient(app) as client:
        resp = client.post("/api/v1/_test_validation", json={})  # missing 'name'

    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in body["error"]
    assert "request_id" in body["error"]


def test_cors_is_configurable():
    # Default config allows any origin; ensure the CORS headers are emitted
    # when a browser-like Origin header is sent.
    app = create_app()
    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "https://example.com"},
        )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
