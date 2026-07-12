"""Health endpoint tests."""


def test_health_endpoint(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_ready_endpoint_schema(client) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert "database" in data["components"]
