
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
from app.models.processing_batch import ProcessingBatch


@pytest.fixture
def processing_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Processing Manager",
            "email": "processing_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000601",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "processing_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "processing_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def processing_setup(db_session):
    location = Location(
        name="Processing Test Zone",
        code="PROC-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Processing Customer",
        email="processing_customer@example.com",
        phone="9000000602",
        customer_type="residential",
        address="Processing Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Processing Recyclable",
        code="PROC-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    db_session.add_all([customer, category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="PROC-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Processing Test Address, Chennai",
        priority="normal",
        status="completed",
    )

    vehicle = Vehicle(
        registration_number="TN-PROC-6001",
        vehicle_name="Processing Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    driver = Workforce(
        employee_code="PROC-DRIVER-01",
        full_name="Processing Driver",
        phone="9000000603",
        role="driver",
        status="available",
        license_number="PROC-LICENSE-01",
    )

    center = RecyclingCenter(
        center_name="Processing Recycling Center",
        center_code="PROC-CENTER-01",
        center_type="material_recovery",
        address="Processing Center Road",
        city="Chennai",
        state="Tamil Nadu",
        total_capacity_kg=1000,
        available_capacity_kg=900,
        status="active",
    )

    db_session.add_all([pickup, vehicle, driver, center])
    db_session.flush()

    assignment = CollectionAssignment(
        assignment_number="PROC-ASN-001",
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
        collection_number="PROC-COL-001",
        assignment_id=assignment.id,
        collected_quantity=100,
        quantity_unit="kg",
        collection_address="Processing Test Address",
        collection_completed_at=datetime.now(timezone.utc),
    )

    db_session.add(collection)
    db_session.flush()

    transfer = WasteTransfer(
        transfer_number="PROC-TRF-001",
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
    db_session.flush()

    segregation = WasteSegregation(
        segregation_number="PROC-SEG-001",
        transfer_id=transfer.id,
        waste_category_id=category.id,
        segregated_quantity=60,
        quantity_unit="kg",
        quality="good",
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    pending_segregation = WasteSegregation(
        segregation_number="PROC-SEG-002",
        transfer_id=transfer.id,
        waste_category_id=category.id,
        segregated_quantity=10,
        quantity_unit="kg",
        quality="good",
        status="pending",
    )

    db_session.add_all([segregation, pending_segregation])
    db_session.commit()

    db_session.refresh(segregation)
    db_session.refresh(pending_segregation)

    return {
        "segregation_id": segregation.id,
        "pending_segregation_id": pending_segregation.id,
    }


def processing_payload(setup):
    return {
        "segregation_id": setup["segregation_id"],
        "processing_method": "sorting",
        "input_quantity": 40,
        "quantity_unit": "kg",
        "notes": "Processing integration test",
    }


def create_processing_batch(client, headers, setup):
    response = client.post(
        "/api/v1/processing/",
        json=processing_payload(setup),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_processing_batch_success(
    client, processing_manager_headers, processing_setup
):
    response = client.post(
        "/api/v1/processing/",
        json=processing_payload(processing_setup),
        headers=processing_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["input_quantity"] == 40
    assert data["recovered_quantity"] == 0
    assert data["rejected_quantity"] == 0
    assert data["recovery_rate"] == 0
    assert data["status"] == "pending"
    assert data["batch_number"].startswith("BAT-")


def test_create_batch_rejects_nonexistent_segregation(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)
    payload["segregation_id"] = 99999

    response = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_create_batch_requires_completed_segregation(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)
    payload["segregation_id"] = processing_setup["pending_segregation_id"]

    response = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_create_batch_rejects_input_above_segregated_quantity(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)
    payload["input_quantity"] = 70

    response = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_create_batches_cannot_exceed_remaining_quantity(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)

    first = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )
    assert first.status_code == 201

    payload["input_quantity"] = 30

    second = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )
    assert second.status_code == 400


def test_create_batch_rejects_invalid_processing_method(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)
    payload["processing_method"] = "unknown"

    response = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )

    assert response.status_code == 422


def test_create_batch_rejects_zero_input_quantity(
    client, processing_manager_headers, processing_setup
):
    payload = processing_payload(processing_setup)
    payload["input_quantity"] = 0

    response = client.post(
        "/api/v1/processing/",
        json=payload,
        headers=processing_manager_headers,
    )

    assert response.status_code == 422


def test_list_processing_batches(
    client, processing_manager_headers, processing_setup
):
    create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.get(
        "/api/v1/processing/",
        headers=processing_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["batches"]) == 1


def test_filter_processing_batches_by_status(
    client, processing_manager_headers, processing_setup
):
    create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.get(
        "/api/v1/processing/",
        params={"status": "pending"},
        headers=processing_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_processing_batches_by_segregation(
    client, processing_manager_headers, processing_setup
):
    create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.get(
        "/api/v1/processing/",
        params={"segregation_id": processing_setup["segregation_id"]},
        headers=processing_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_processing_batch(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.get(
        f"/api/v1/processing/{batch['id']}",
        headers=processing_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == batch["id"]


def test_get_nonexistent_processing_batch(
    client, processing_manager_headers
):
    response = client.get(
        "/api/v1/processing/99999",
        headers=processing_manager_headers,
    )

    assert response.status_code == 404


def test_update_pending_batch_and_recovery_rate(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.patch(
        f"/api/v1/processing/{batch['id']}",
        json={
            "recovered_quantity": 25,
            "rejected_quantity": 5,
        },
        headers=processing_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["recovered_quantity"] == 25
    assert response.json()["rejected_quantity"] == 5
    assert response.json()["recovery_rate"] == 62.5


def test_update_rejects_recovered_and_rejected_above_input(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.patch(
        f"/api/v1/processing/{batch['id']}",
        json={
            "recovered_quantity": 30,
            "rejected_quantity": 15,
        },
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_update_input_quantity_checks_segregation_limit(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.patch(
        f"/api/v1/processing/{batch['id']}",
        json={"input_quantity": 70},
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_processing_status_workflow(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    progress = client.patch(
        f"/api/v1/processing/{batch['id']}/status",
        json={"status": "in_progress"},
        headers=processing_manager_headers,
    )

    assert progress.status_code == 200
    assert progress.json()["status"] == "in_progress"
    assert progress.json()["started_at"] is not None

    completed = client.patch(
        f"/api/v1/processing/{batch['id']}/status",
        json={"status": "completed"},
        headers=processing_manager_headers,
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None


def test_processing_rejects_invalid_status_transition(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.patch(
        f"/api/v1/processing/{batch['id']}/status",
        json={"status": "completed"},
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_processing_rejects_invalid_status_value(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.patch(
        f"/api/v1/processing/{batch['id']}/status",
        json={"status": "unknown"},
        headers=processing_manager_headers,
    )

    assert response.status_code == 422


def test_delete_pending_processing_batch(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    response = client.delete(
        f"/api/v1/processing/{batch['id']}",
        headers=processing_manager_headers,
    )

    assert response.status_code == 204


def test_delete_in_progress_batch_rejected(
    client, processing_manager_headers, processing_setup
):
    batch = create_processing_batch(
        client, processing_manager_headers, processing_setup
    )

    client.patch(
        f"/api/v1/processing/{batch['id']}/status",
        json={"status": "in_progress"},
        headers=processing_manager_headers,
    )

    response = client.delete(
        f"/api/v1/processing/{batch['id']}",
        headers=processing_manager_headers,
    )

    assert response.status_code == 400


def test_unauthorized_processing_access(client):
    response = client.get("/api/v1/processing/")

    assert response.status_code == 401
