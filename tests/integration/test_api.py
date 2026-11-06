from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_openapi_documentation():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "paths" in response.json()


def test_unauthorized_access():
    response = client.get("/api/v1/users/me")

    assert response.status_code in (401, 403)