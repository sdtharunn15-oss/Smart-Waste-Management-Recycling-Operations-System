
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.models.location import Location
from app.models.customer import Customer
from app.models.waste_category import WasteCategory
from app.models.pickup_request import PickupRequest
from app.models.vehicle import Vehicle
from app.models.workforce import Workforce
from app.models.assignment import CollectionAssignment
from app.models.collection import CollectionRecord
from app.models.recycling_center import RecyclingCenter
from app.models.waste_transfer import WasteTransfer
from app.models.segregation import WasteSegregation


@pytest.fixture
def segregation_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Segregation Manager",
            "email": "segregation_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000501",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "segregation_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "segregation_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def segregation_setup(db_session):
    location = Location(
        name="Segregation Test Zone",
        code="SEG-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Segregation Customer",
        email="seg_customer@example.com",
        phone="9000000502",
        customer_type="residential",
        address="Segregation Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Segregation Recyclable",
        code="SEG-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    inactive_category = WasteCategory(
        name="Inactive Segregation Category",
        code="SEG-INACTIVE",
        waste_type="general",
        is_recyclable=False,
        default_unit="kg",
        status="inactive",
    )

    db_session.add_all([customer, category, inactive_category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="SEG-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Segregation Test Address, Chennai",
        priority="normal",
        status="completed",
    )

    vehicle = Vehicle(
        registration_number="TN-SEG-5001",
        vehicle_name="Segregation Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    driver = Workforce(
        employee_code="SEG-DRIVER-01",
        full_name="Segregation Driver",
        phone="9000000503",
        role="driver",
        status="available",
        license_number="SEG-LICENSE-01",
    )

    center = RecyclingCenter(
        center_name="Segregation Recycling Center",
        center_code="SEG-CENTER-01",
        center_type="material_recovery",
        address="Segregation Center Road",
        city="Chennai",
        state="Tamil Nadu",
        total_capacity_kg=1000,
        available_capacity_kg=900,
        status="active",
    )

    db_session.add_all([pickup, vehicle, driver, center])
    db_session.flush()

    assignment = CollectionAssignment(
        assignment_number="SEG-ASN-001",
        pickup_request_id=pickup.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    db_session.add(assignment)
    db_session.flush()

    collection = CollectionRecord(
        collection_number="SEG-COL-001",
        assignment_id=assignment.id,
        collected_quantity=100,
        quantity_unit="kg",
        collection_address="Segregation Test Address",
        collection_completed_at=datetime.now(timezone.utc),
    )

    db_session.add(collection)
    db_session.flush()

    transfer = WasteTransfer(
        transfer_number="SEG-TRF-001",
        collection_id=collection.id,
        recycling_center_id=center.id,
        transferred_quantity=80,
        quantity_unit="kg",
        transfer_type="direct",
        status="received",
        transferred_at=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
    )

    db_session.add(transfer)
    db_session.commit()

    db_session.refresh(transfer)
    db_session.refresh(category)
    db_session.refresh(inactive_category)

    return {
        "transfer_id": transfer.id,
        "category_id": category.id,
        "inactive_category_id": inactive_category.id,
    }


def segregation_payload(setup):
    return {
        "transfer_id": setup["transfer_id"],
        "waste_category_id": setup["category_id"],
        "segregated_quantity": 40,
        "quantity_unit": "kg",
        "quality": "good",
        "notes": "Segregation integration test",
    }


def test_create_segregation_success(
    client, segregation_manager_headers, segregation_setup
):
    response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["segregated_quantity"] == 40
    assert data["status"] == "pending"
    assert data["quality"] == "good"
    assert data["segregation_number"].startswith("SEG-")


def test_create_segregation_nonexistent_transfer(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["transfer_id"] = 99999

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_create_segregation_nonexistent_category(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["waste_category_id"] = 99999

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_create_segregation_inactive_category(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["waste_category_id"] = segregation_setup["inactive_category_id"]

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_create_segregation_quantity_exceeds_transfer(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["segregated_quantity"] = 100

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_create_segregation_rejects_invalid_quality(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["quality"] = "unknown"

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 422


def test_create_segregation_rejects_zero_quantity(
    client, segregation_manager_headers, segregation_setup
):
    payload = segregation_payload(segregation_setup)
    payload["segregated_quantity"] = 0

    response = client.post(
        "/api/v1/segregation/",
        json=payload,
        headers=segregation_manager_headers,
    )

    assert response.status_code == 422


def test_create_segregation_requires_received_transfer(
    client, segregation_manager_headers, segregation_setup, db_session
):
    transfer = db_session.get(
        WasteTransfer, segregation_setup["transfer_id"]
    )
    transfer.status = "in_transit"
    db_session.commit()

    response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_list_segregations(
    client, segregation_manager_headers, segregation_setup
):
    client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )

    response = client.get(
        "/api/v1/segregation/",
        headers=segregation_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["segregations"]) == 1


def test_filter_segregations_by_transfer(
    client, segregation_manager_headers, segregation_setup
):
    client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )

    response = client.get(
        "/api/v1/segregation/",
        params={"transfer_id": segregation_setup["transfer_id"]},
        headers=segregation_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_nonexistent_segregation(
    client, segregation_manager_headers
):
    response = client.get(
        "/api/v1/segregation/99999",
        headers=segregation_manager_headers,
    )

    assert response.status_code == 404


def test_update_pending_segregation(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/segregation/{segregation_id}",
        json={"segregated_quantity": 50, "quality": "excellent"},
        headers=segregation_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["segregated_quantity"] == 50
    assert response.json()["quality"] == "excellent"


def test_update_rejects_quantity_above_transfer(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/segregation/{segregation_id}",
        json={"segregated_quantity": 90},
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_segregation_status_workflow(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    progress_response = client.patch(
        f"/api/v1/segregation/{segregation_id}/status",
        json={"status": "in_progress"},
        headers=segregation_manager_headers,
    )

    assert progress_response.status_code == 200
    assert progress_response.json()["status"] == "in_progress"
    assert progress_response.json()["started_at"] is not None

    completed_response = client.patch(
        f"/api/v1/segregation/{segregation_id}/status",
        json={"status": "completed"},
        headers=segregation_manager_headers,
    )

    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert completed_response.json()["completed_at"] is not None


def test_segregation_rejects_invalid_status_transition(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/segregation/{segregation_id}/status",
        json={"status": "completed"},
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_delete_pending_segregation(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/segregation/{segregation_id}",
        headers=segregation_manager_headers,
    )

    assert response.status_code == 204


def test_delete_completed_segregation_rejected(
    client, segregation_manager_headers, segregation_setup
):
    create_response = client.post(
        "/api/v1/segregation/",
        json=segregation_payload(segregation_setup),
        headers=segregation_manager_headers,
    )
    segregation_id = create_response.json()["id"]

    client.patch(
        f"/api/v1/segregation/{segregation_id}/status",
        json={"status": "in_progress"},
        headers=segregation_manager_headers,
    )

    client.patch(
        f"/api/v1/segregation/{segregation_id}/status",
        json={"status": "completed"},
        headers=segregation_manager_headers,
    )

    response = client.delete(
        f"/api/v1/segregation/{segregation_id}",
        headers=segregation_manager_headers,
    )

    assert response.status_code == 400


def test_unauthorized_segregation_access(client):
    response = client.get("/api/v1/segregation/")

    assert response.status_code == 401
