
from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.maintenance import VehicleMaintenance


@pytest.fixture
def maintenance_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Maintenance Manager",
            "email": "maintenance_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000801",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "maintenance_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "maintenance_manager@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def maintenance_setup(db_session):
    vehicle = Vehicle(
        registration_number="TN-MNT-8001",
        vehicle_name="Maintenance Test Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    on_route_vehicle = Vehicle(
        registration_number="TN-MNT-8002",
        vehicle_name="On Route Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="on_route",
    )

    inactive_vehicle = Vehicle(
        registration_number="TN-MNT-8003",
        vehicle_name="Inactive Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="inactive",
    )

    db_session.add_all([
        vehicle,
        on_route_vehicle,
        inactive_vehicle,
    ])
    db_session.commit()

    db_session.refresh(vehicle)
    db_session.refresh(on_route_vehicle)
    db_session.refresh(inactive_vehicle)

    return {
        "vehicle_id": vehicle.id,
        "on_route_vehicle_id": on_route_vehicle.id,
        "inactive_vehicle_id": inactive_vehicle.id,
    }


def maintenance_payload(setup):
    return {
        "vehicle_id": setup["vehicle_id"],
        "maintenance_type": "routine_service",
        "priority": "normal",
        "description": "Regular vehicle maintenance service",
        "scheduled_date": (
            datetime.now(timezone.utc) + timedelta(days=3)
        ).isoformat(),
        "service_provider": "Chennai Auto Services",
        "cost": 2500,
        "odometer_reading": 25000,
        "notes": "Scheduled maintenance test",
    }


def create_maintenance(client, headers, setup):
    response = client.post(
        "/api/v1/maintenance/",
        json=maintenance_payload(setup),
        headers=headers,
    )

    assert response.status_code == 201
    return response.json()


def test_create_maintenance_success(
    client, maintenance_manager_headers, maintenance_setup, db_session
):
    response = client.post(
        "/api/v1/maintenance/",
        json=maintenance_payload(maintenance_setup),
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["vehicle_id"] == maintenance_setup["vehicle_id"]
    assert data["status"] == "scheduled"
    assert data["maintenance_number"].startswith("MNT-")

    vehicle = db_session.get(
        Vehicle, maintenance_setup["vehicle_id"]
    )
    assert vehicle.status == "maintenance"


def test_create_maintenance_with_default_values(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload.pop("priority")

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 201
    assert response.json()["priority"] == "normal"


def test_create_maintenance_vehicle_not_found(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["vehicle_id"] = 99999

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_create_maintenance_vehicle_on_route(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["vehicle_id"] = maintenance_setup["on_route_vehicle_id"]

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_create_maintenance_inactive_vehicle(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["vehicle_id"] = maintenance_setup["inactive_vehicle_id"]

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_create_maintenance_rejects_past_date(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["scheduled_date"] = (
        datetime.now(timezone.utc) - timedelta(days=2)
    ).isoformat()

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_create_duplicate_active_maintenance_rejected(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.post(
        "/api/v1/maintenance/",
        json=maintenance_payload(maintenance_setup),
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_create_maintenance_invalid_type(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["maintenance_type"] = "invalid_type"

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 422


def test_create_maintenance_invalid_priority(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["priority"] = "invalid_priority"

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 422


def test_create_maintenance_negative_cost(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["cost"] = -100

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 422


def test_create_maintenance_invalid_description(
    client, maintenance_manager_headers, maintenance_setup
):
    payload = maintenance_payload(maintenance_setup)
    payload["description"] = "AB"

    response = client.post(
        "/api/v1/maintenance/",
        json=payload,
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 422


def test_list_maintenance_records(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        "/api/v1/maintenance/",
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["maintenance_records"]) == 1


def test_filter_maintenance_by_vehicle(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        "/api/v1/maintenance/",
        params={"vehicle_id": maintenance_setup["vehicle_id"]},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_maintenance_by_status(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        "/api/v1/maintenance/",
        params={"status": "scheduled"},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_maintenance_by_type(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        "/api/v1/maintenance/",
        params={"maintenance_type": "routine_service"},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_maintenance_by_priority(
    client, maintenance_manager_headers, maintenance_setup
):
    create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        "/api/v1/maintenance/",
        params={"priority": "normal"},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_maintenance_details(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.get(
        f"/api/v1/maintenance/{record['id']}",
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == record["id"]


def test_get_nonexistent_maintenance(
    client, maintenance_manager_headers
):
    response = client.get(
        "/api/v1/maintenance/99999",
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 404


def test_update_scheduled_maintenance(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}",
        json={
            "description": "Updated vehicle service",
            "cost": 3500,
            "priority": "high",
        },
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated vehicle service"
    assert response.json()["cost"] == 3500
    assert response.json()["priority"] == "high"


def test_update_maintenance_rejects_past_date(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}",
        json={
            "scheduled_date": (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).isoformat()
        },
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_update_nonexistent_maintenance(
    client, maintenance_manager_headers
):
    response = client.patch(
        "/api/v1/maintenance/99999",
        json={"cost": 1000},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_maintenance_start_workflow(
    client, maintenance_manager_headers, maintenance_setup, db_session
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={
            "status": "in_progress",
            "notes": "Service started",
        },
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["started_at"] is not None

    vehicle = db_session.get(
        Vehicle, maintenance_setup["vehicle_id"]
    )
    assert vehicle.status == "maintenance"


def test_maintenance_completion_releases_vehicle(
    client, maintenance_manager_headers, maintenance_setup, db_session
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={"status": "in_progress"},
        headers=maintenance_manager_headers,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={
            "status": "completed",
            "notes": "Maintenance completed",
        },
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None

    vehicle = db_session.get(
        Vehicle, maintenance_setup["vehicle_id"]
    )
    assert vehicle.status == "available"


def test_maintenance_cancellation_releases_vehicle(
    client, maintenance_manager_headers, maintenance_setup, db_session
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={
            "status": "cancelled",
            "notes": "Maintenance cancelled",
        },
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    vehicle = db_session.get(
        Vehicle, maintenance_setup["vehicle_id"]
    )
    assert vehicle.status == "available"


def test_maintenance_rejects_invalid_transition(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={"status": "completed"},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_completed_maintenance_cannot_be_updated(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={"status": "in_progress"},
        headers=maintenance_manager_headers,
    )

    client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={"status": "completed"},
        headers=maintenance_manager_headers,
    )

    response = client.patch(
        f"/api/v1/maintenance/{record['id']}",
        json={"cost": 5000},
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_delete_scheduled_maintenance(
    client, maintenance_manager_headers, maintenance_setup, db_session
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    response = client.delete(
        f"/api/v1/maintenance/{record['id']}",
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 204

    vehicle = db_session.get(
        Vehicle, maintenance_setup["vehicle_id"]
    )
    assert vehicle.status == "available"


def test_delete_in_progress_maintenance_rejected(
    client, maintenance_manager_headers, maintenance_setup
):
    record = create_maintenance(
        client,
        maintenance_manager_headers,
        maintenance_setup,
    )

    client.patch(
        f"/api/v1/maintenance/{record['id']}/status",
        json={"status": "in_progress"},
        headers=maintenance_manager_headers,
    )

    response = client.delete(
        f"/api/v1/maintenance/{record['id']}",
        headers=maintenance_manager_headers,
    )

    assert response.status_code == 400


def test_unauthorized_maintenance_access(client):
    response = client.get("/api/v1/maintenance/")

    assert response.status_code == 401
