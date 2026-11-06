
import pytest

from app.models.user import User
from app.models.recycling_center import RecyclingCenter


@pytest.fixture
def recycling_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Recycling Manager",
            "email": "recycling_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000301",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "recycling_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "recycling_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def center_payload():
    return {
        "center_name": "Chennai Recycling Center",
        "center_code": "CHN-REC-001",
        "center_type": "material_recovery",
        "address": "Test Industrial Road, Chennai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "postal_code": "600001",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "total_capacity_kg": 10000,
        "operating_hours": "9 AM - 6 PM",
        "contact_phone": "9000000302",
        "contact_email": "center@example.com",
        "notes": "Integration test center",
    }


def test_create_recycling_center_success(
    client, recycling_manager_headers, center_payload
):
    response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["center_name"] == center_payload["center_name"]
    assert data["center_code"] == "CHN-REC-001"
    assert data["center_type"] == "material_recovery"
    assert data["total_capacity_kg"] == 10000
    assert data["available_capacity_kg"] == 10000
    assert data["status"] == "active"


def test_create_duplicate_center_code(
    client, recycling_manager_headers, center_payload
):
    first = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    assert first.status_code == 201

    duplicate_payload = center_payload.copy()
    duplicate_payload["center_name"] = "Another Recycling Center"
    duplicate_payload["center_code"] = " chn-rec-001 "

    response = client.post(
        "/api/v1/recycling-centers/",
        json=duplicate_payload,
        headers=recycling_manager_headers,
    )

    assert response.status_code == 409


def test_create_center_invalid_type(
    client, recycling_manager_headers, center_payload
):
    payload = center_payload.copy()
    payload["center_type"] = "invalid_type"

    response = client.post(
        "/api/v1/recycling-centers/",
        json=payload,
        headers=recycling_manager_headers,
    )

    assert response.status_code == 400


def test_create_center_invalid_capacity(
    client, recycling_manager_headers, center_payload
):
    payload = center_payload.copy()
    payload["total_capacity_kg"] = 0

    response = client.post(
        "/api/v1/recycling-centers/",
        json=payload,
        headers=recycling_manager_headers,
    )

    assert response.status_code == 422


def test_list_recycling_centers(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/recycling-centers/",
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["centers"]) == 1


def test_filter_centers_by_city(
    client, recycling_manager_headers, center_payload
):
    client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )

    response = client.get(
        "/api/v1/recycling-centers/?city=Chennai",
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_centers_invalid_type(
    client, recycling_manager_headers
):
    response = client.get(
        "/api/v1/recycling-centers/?center_type=invalid",
        headers=recycling_manager_headers,
    )

    assert response.status_code == 400


def test_get_nonexistent_center(
    client, recycling_manager_headers
):
    response = client.get(
        "/api/v1/recycling-centers/99999",
        headers=recycling_manager_headers,
    )

    assert response.status_code == 404


def test_update_center_success(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    center_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/recycling-centers/{center_id}",
        json={"center_name": "Updated Chennai Recycling Center"},
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["center_name"] == "Updated Chennai Recycling Center"


def test_update_capacity_success(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    center_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/recycling-centers/{center_id}",
        json={"total_capacity_kg": 15000},
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total_capacity_kg"] == 15000
    assert response.json()["available_capacity_kg"] == 15000


def test_change_center_status(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    center_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/recycling-centers/{center_id}/status",
        json={"status": "maintenance"},
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"


def test_change_center_invalid_status(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    center_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/recycling-centers/{center_id}/status",
        json={"status": "closed"},
        headers=recycling_manager_headers,
    )

    assert response.status_code == 400


def test_delete_center(
    client, recycling_manager_headers, center_payload
):
    create_response = client.post(
        "/api/v1/recycling-centers/",
        json=center_payload,
        headers=recycling_manager_headers,
    )
    center_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/recycling-centers/{center_id}",
        headers=recycling_manager_headers,
    )

    assert response.status_code == 200

    get_response = client.get(
        f"/api/v1/recycling-centers/{center_id}",
        headers=recycling_manager_headers,
    )

    assert get_response.status_code == 404


def test_unauthorized_center_access(client):
    response = client.get("/api/v1/recycling-centers/")
    assert response.status_code == 401
