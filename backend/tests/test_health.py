def test_server_starts(client):
    # If we reach here the app imported and TestClient started it.
    assert client is not None


def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["service"] == "xyz-ai-backend"
    assert body["data"]["status"] == "healthy"


def test_request_id_present_on_response(client):
    resp = client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Request-ID"].startswith("req_")


def test_client_supplied_request_id_is_preserved(client):
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "req_custom_123"})
    assert resp.headers["X-Request-ID"] == "req_custom_123"


def test_invalid_endpoint_returns_standardized_error(client):
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body["error"]
    assert body["error"]["request_id"] == resp.headers["X-Request-ID"]
