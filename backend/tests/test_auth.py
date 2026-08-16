import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.auth.provider import TokenVerificationError, set_token_verifier


class FakeVerifier:
    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode

    def verify_id_token(self, token: str):
        if self.mode == "valid":
            return {
                "uid": "user_123",
                "email": "student@example.com",
                "name": "Test User",
            }
        if self.mode == "no_uid":
            return {"email": "x@example.com"}
        raise TokenVerificationError("verification failed")


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c
    # Reset to the default (Firebase) verifier after each test.
    set_token_verifier(None)


def test_auth_me_valid_token(client):
    set_token_verifier(FakeVerifier("valid"))
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer valid.token.value"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["firebase_uid"] == "user_123"
    assert body["data"]["email"] == "student@example.com"
    assert body["data"]["name"] == "Test User"


def test_auth_me_missing_token(client):
    set_token_verifier(FakeVerifier("valid"))
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_auth_me_invalid_token(client):
    set_token_verifier(FakeVerifier("invalid"))
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_me_expired_token(client):
    # Expired/revoked tokens follow the same 401 path as any bad token.
    set_token_verifier(FakeVerifier("invalid"))
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer expired.token.value"},
    )
    assert resp.status_code == 401


def test_auth_me_token_missing_uid(client):
    set_token_verifier(FakeVerifier("no_uid"))
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer some.token"},
    )
    assert resp.status_code == 401
