
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
from app.models.disposal import WasteDisposal


@pytest.fixture
def disposal_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Disposal Manager",
            "email": "disposal_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000701",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "disposal_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "disposal_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def disposal_setup(db_session):
    location = Location(
        name="Disposal Test Zone",
        code="DSP-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Disposal Customer",
        email="disposal_customer@example.com",
        phone="9000000702",
        customer_type="residential",
        address="Disposal Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Disposal Recyclable",
        code="DSP-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    inactive_category = WasteCategory(
        name="Inactive Disposal Category",
        code="DSP-INACTIVE",
        waste_type="general",
        is_recyclable=False,
        default_unit="kg",
        status="inactive",
    )

    db_session.add_all([customer, category, inactive_category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="DSP-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Disposal Test Address, Chennai",
        priority="normal",
        status="completed",
    )

    vehicle = Vehicle(
        registration_number="TN-DSP-7001",
        vehicle_name="Disposal Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    driver = Workforce(
        employee_code="DSP-DRIVER-01",
        full_name="Disposal Driver",
        phone="9000000703",
        role="driver",
        status="available",
        license_number="DSP-LICENSE-01",
    )

    center = RecyclingCenter(
        center_name="Disposal Recycling Center",
        center_code="DSP-CENTER-01",
        center_type="material_recovery",
        address="Disposal Center Road",
        city="Chennai",
        state="Tamil Nadu",
        total_capacity_kg=1000,
        available_capacity_kg=900,
        status="active",
    )

    db_session.add_all([pickup, vehicle, driver, center])
    db_session.flush()

    assignment = CollectionAssignment(
        assignment_number="DSP-ASN-001",
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
        collection_number="DSP-COL-001",
        assignment_id=assignment.id,
        collected_quantity=100,
        quantity_unit="kg",
        collection_address="Disposal Test Address",
        collection_completed_at=datetime.now(timezone.utc),
    )

    db_session.add(collection)
    db_session.flush()

    transfer = WasteTransfer(
        transfer_number="DSP-TRF-001",
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
        segregation_number="DSP-SEG-001",
        transfer_id=transfer.id,
        waste_category_id=category.id,
        segregated_quantity=30,
        quantity_unit="kg",
        quality="good",
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    pending_segregation = WasteSegregation(
        segregation_number="DSP-SEG-002",
        transfer_id=transfer.id,
        waste_category_id=category.id,
        segregated_quantity=10,
        quantity_unit="kg",
        quality="good",
        status="pending",
    )

    db_session.add_all([segregation, pending_segregation])
    db_session.flush()

    batch = ProcessingBatch(
        batch_number="DSP-BATCH-001",
        segregation_id=segregation.id,
        processing_method="sorting",
        input_quantity=30,
        recovered_quantity=10,
        rejected_quantity=5,
        quantity_unit="kg",
        recovery_rate=33.33,
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    pending_batch = ProcessingBatch(
        batch_number="DSP-BATCH-002",
        segregation_id=segregation.id,
        processing_method="sorting",
        input_quantity=10,
        recovered_quantity=0,
        rejected_quantity=0,
        quantity_unit="kg",
        recovery_rate=0,
        status="pending",
    )

    db_session.add_all([batch, pending_batch])
    db_session.commit()

    db_session.refresh(category)
    db_session.refresh(inactive_category)
    db_session.refresh(batch)
    db_session.refresh(pending_batch)
    db_session.refresh(transfer)

    return {
        "category_id": category.id,
        "inactive_category_id": inactive_category.id,
        "batch_id": batch.id,
        "pending_batch_id": pending_batch.id,
        "transfer_id": transfer.id,
    }


def disposal_payload(setup):
    return {
        "processing_batch_id": setup["batch_id"],
        "waste_category_id": setup["category_id"],
        "disposal_method": "landfill",
        "quantity": 10,
        "quantity_unit": "kg",
        "disposal_location": "Chennai Disposal Facility",
        "disposal_date": datetime.now(timezone.utc).isoformat(),
        "notes": "Disposal integration test",
    }


def create_disposal(client, headers, setup):
    response = client.post(
        "/api/v1/disposal/",
        json=disposal_payload(setup),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_disposal_from_processing_batch(
    client, disposal_manager_headers, disposal_setup
):
    response = client.post(
        "/api/v1/disposal/",
        json=disposal_payload(disposal_setup),
        headers=disposal_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["quantity"] == 10
    assert data["status"] == "pending"
    assert data["processing_batch_id"] == disposal_setup["batch_id"]
    assert data["disposal_number"].startswith("DSP-")


def test_create_disposal_from_received_transfer(
    client, disposal_manager_headers, disposal_setup
):
    payload = {
        "transfer_id": disposal_setup["transfer_id"],
        "waste_category_id": disposal_setup["category_id"],
        "disposal_method": "incineration",
        "quantity": 20,
        "quantity_unit": "kg",
        "disposal_location": "Chennai Disposal Facility",
        "disposal_date": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 201
    assert response.json()["transfer_id"] == disposal_setup["transfer_id"]
    assert response.json()["quantity"] == 20


def test_create_disposal_requires_source(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload.pop("processing_batch_id")

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_rejects_nonexistent_batch(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["processing_batch_id"] = 99999

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_requires_completed_batch(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["processing_batch_id"] = disposal_setup["pending_batch_id"]

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_rejects_quantity_above_batch_remaining(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["quantity"] = 21

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposals_cannot_exceed_batch_remaining(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)

    first = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )
    assert first.status_code == 201

    # Batch availability: 30 input - 10 recovered = 20 kg.
    # First disposal uses 10 kg, so only 10 kg remains.
    # A second disposal of 11 kg must be rejected.
    payload["quantity"] = 11

    second = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert second.status_code == 400


def test_create_disposal_rejects_nonexistent_transfer(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload.pop("processing_batch_id")
    payload["transfer_id"] = 99999

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_requires_received_transfer(
    client, disposal_manager_headers, disposal_setup, db_session
):
    transfer = db_session.get(
        WasteTransfer, disposal_setup["transfer_id"]
    )
    transfer.status = "in_transit"
    db_session.commit()

    payload = disposal_payload(disposal_setup)
    payload.pop("processing_batch_id")
    payload["transfer_id"] = disposal_setup["transfer_id"]

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_transfer_disposal_respects_unsegregated_quantity(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload.pop("processing_batch_id")
    payload["transfer_id"] = disposal_setup["transfer_id"]
    payload["quantity"] = 51

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_rejects_inactive_category(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["waste_category_id"] = disposal_setup["inactive_category_id"]

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_rejects_future_date(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["disposal_date"] = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).isoformat()

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_create_disposal_rejects_invalid_method(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["disposal_method"] = "unknown"

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 422


def test_create_disposal_rejects_zero_quantity(
    client, disposal_manager_headers, disposal_setup
):
    payload = disposal_payload(disposal_setup)
    payload["quantity"] = 0

    response = client.post(
        "/api/v1/disposal/",
        json=payload,
        headers=disposal_manager_headers,
    )

    assert response.status_code == 422


def test_list_disposals(
    client, disposal_manager_headers, disposal_setup
):
    create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.get(
        "/api/v1/disposal/",
        headers=disposal_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["disposals"]) == 1


def test_filter_disposals_by_status(
    client, disposal_manager_headers, disposal_setup
):
    create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.get(
        "/api/v1/disposal/",
        params={"status": "pending"},
        headers=disposal_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_disposals_by_method(
    client, disposal_manager_headers, disposal_setup
):
    create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.get(
        "/api/v1/disposal/",
        params={"disposal_method": "landfill"},
        headers=disposal_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_disposal_details(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.get(
        f"/api/v1/disposal/{disposal['id']}",
        headers=disposal_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == disposal["id"]


def test_get_nonexistent_disposal(
    client, disposal_manager_headers
):
    response = client.get(
        "/api/v1/disposal/99999",
        headers=disposal_manager_headers,
    )

    assert response.status_code == 404


def test_update_pending_disposal(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.patch(
        f"/api/v1/disposal/{disposal['id']}",
        json={
            "quantity": 12,
            "disposal_location": "Updated Disposal Facility",
        },
        headers=disposal_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 12
    assert response.json()["disposal_location"] == "Updated Disposal Facility"


def test_update_disposal_rejects_excess_quantity(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.patch(
        f"/api/v1/disposal/{disposal['id']}",
        json={"quantity": 21},
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_disposal_approval_workflow(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    approval = client.patch(
        f"/api/v1/disposal/{disposal['id']}/status",
        json={"status": "approved", "notes": "Approved for disposal"},
        headers=disposal_manager_headers,
    )

    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"
    assert approval.json()["approved_by"] is not None

    completed = client.patch(
        f"/api/v1/disposal/{disposal['id']}/status",
        json={"status": "completed"},
        headers=disposal_manager_headers,
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_disposal_rejects_invalid_status_transition(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.patch(
        f"/api/v1/disposal/{disposal['id']}/status",
        json={"status": "completed"},
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_delete_pending_disposal(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    response = client.delete(
        f"/api/v1/disposal/{disposal['id']}",
        headers=disposal_manager_headers,
    )

    assert response.status_code == 204


def test_delete_approved_disposal_rejected(
    client, disposal_manager_headers, disposal_setup
):
    disposal = create_disposal(
        client, disposal_manager_headers, disposal_setup
    )

    client.patch(
        f"/api/v1/disposal/{disposal['id']}/status",
        json={"status": "approved"},
        headers=disposal_manager_headers,
    )

    response = client.delete(
        f"/api/v1/disposal/{disposal['id']}",
        headers=disposal_manager_headers,
    )

    assert response.status_code == 400


def test_unauthorized_disposal_access(client):
    response = client.get("/api/v1/disposal/")

    assert response.status_code == 401
