
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


@pytest.fixture
def transfer_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Transfer Manager",
            "email": "transfer_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000401",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "transfer_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "transfer_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def transfer_setup(db_session):
    location = Location(
        name="Transfer Test Zone",
        code="TRF-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Transfer Customer",
        email="transfer_customer@example.com",
        phone="9000000402",
        customer_type="residential",
        address="Transfer Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Transfer Recyclable",
        code="TRF-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    db_session.add_all([customer, category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="TRF-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Transfer Test Address, Chennai",
        priority="normal",
        status="completed",
    )

    vehicle = Vehicle(
        registration_number="TN-TRF-4001",
        vehicle_name="Transfer Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    driver = Workforce(
        employee_code="TRF-DRIVER-01",
        full_name="Transfer Driver",
        phone="9000000403",
        role="driver",
        status="available",
        license_number="TRF-LICENSE-01",
    )

    center = RecyclingCenter(
        center_name="Transfer Recycling Center",
        center_code="TRF-CENTER-01",
        center_type="material_recovery",
        address="Transfer Center Road",
        city="Chennai",
        state="Tamil Nadu",
        total_capacity_kg=1000,
        available_capacity_kg=1000,
        status="active",
    )

    db_session.add_all([pickup, vehicle, driver, center])
    db_session.flush()

    assignment = CollectionAssignment(
        assignment_number="TRF-ASN-001",
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
        collection_number="TRF-COL-001",
        assignment_id=assignment.id,
        collected_quantity=100,
        quantity_unit="kg",
        collection_address="Transfer Test Address",
        collection_completed_at=datetime.now(timezone.utc),
    )

    db_session.add(collection)
    db_session.commit()

    db_session.refresh(collection)
    db_session.refresh(center)

    return {
        "collection_id": collection.id,
        "center_id": center.id,
    }


def transfer_payload(setup):
    return {
        "collection_id": setup["collection_id"],
        "recycling_center_id": setup["center_id"],
        "transferred_quantity": 60,
        "quantity_unit": "kg",
        "transfer_type": "direct",
        "notes": "Integration test transfer",
    }


def test_create_transfer_success(
    client, transfer_manager_headers, transfer_setup, db_session
):
    response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["transferred_quantity"] == 60
    assert data["status"] == "pending"
    assert data["transfer_number"].startswith("TRF-")

    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    assert center.available_capacity_kg == 940


def test_transfer_rejects_nonexistent_collection(
    client, transfer_manager_headers, transfer_setup
):
    payload = transfer_payload(transfer_setup)
    payload["collection_id"] = 99999

    response = client.post(
        "/api/v1/transfers/",
        json=payload,
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_rejects_nonexistent_center(
    client, transfer_manager_headers, transfer_setup
):
    payload = transfer_payload(transfer_setup)
    payload["recycling_center_id"] = 99999

    response = client.post(
        "/api/v1/transfers/",
        json=payload,
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_rejects_inactive_center(
    client, transfer_manager_headers, transfer_setup, db_session
):
    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    center.status = "inactive"
    db_session.commit()

    response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_rejects_quantity_above_collection(
    client, transfer_manager_headers, transfer_setup
):
    payload = transfer_payload(transfer_setup)
    payload["transferred_quantity"] = 150

    response = client.post(
        "/api/v1/transfers/",
        json=payload,
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_rejects_insufficient_center_capacity(
    client, transfer_manager_headers, transfer_setup, db_session
):
    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    center.available_capacity_kg = 20
    db_session.commit()

    response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_rejects_unavailable_vehicle(
    client, transfer_manager_headers, transfer_setup, db_session
):
    vehicle = Vehicle(
        registration_number="TN-TRF-4002",
        vehicle_name="Unavailable Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="maintenance",
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)

    payload = transfer_payload(transfer_setup)
    payload["vehicle_id"] = vehicle.id

    response = client.post(
        "/api/v1/transfers/",
        json=payload,
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_transfer_status_workflow(
    client, transfer_manager_headers, transfer_setup
):
    create_response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )
    assert create_response.status_code == 201

    transfer_id = create_response.json()["id"]

    transit_response = client.patch(
        f"/api/v1/transfers/{transfer_id}/status",
        json={"status": "in_transit"},
        headers=transfer_manager_headers,
    )
    assert transit_response.status_code == 200
    assert transit_response.json()["status"] == "in_transit"

    received_response = client.patch(
        f"/api/v1/transfers/{transfer_id}/status",
        json={"status": "received"},
        headers=transfer_manager_headers,
    )
    assert received_response.status_code == 200
    assert received_response.json()["status"] == "received"


def test_transfer_rejects_invalid_status_transition(
    client, transfer_manager_headers, transfer_setup
):
    create_response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )
    transfer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/transfers/{transfer_id}/status",
        json={"status": "received"},
        headers=transfer_manager_headers,
    )

    assert response.status_code == 400


def test_cancel_transfer_restores_center_capacity(
    client, transfer_manager_headers, transfer_setup, db_session
):
    create_response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )
    transfer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/transfers/{transfer_id}/status",
        json={"status": "cancelled"},
        headers=transfer_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    assert center.available_capacity_kg == 1000


def test_list_transfers(
    client, transfer_manager_headers, transfer_setup
):
    client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )

    response = client.get(
        "/api/v1/transfers/",
        headers=transfer_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["transfers"]) == 1


def test_get_nonexistent_transfer(
    client, transfer_manager_headers
):
    response = client.get(
        "/api/v1/transfers/99999",
        headers=transfer_manager_headers,
    )

    assert response.status_code == 404


def test_update_pending_transfer(
    client, transfer_manager_headers, transfer_setup, db_session
):
    create_response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )
    transfer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/transfers/{transfer_id}",
        json={"transferred_quantity": 80},
        headers=transfer_manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["transferred_quantity"] == 80

    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    assert center.available_capacity_kg == 920


def test_delete_pending_transfer_restores_capacity(
    client, transfer_manager_headers, transfer_setup, db_session
):
    create_response = client.post(
        "/api/v1/transfers/",
        json=transfer_payload(transfer_setup),
        headers=transfer_manager_headers,
    )
    transfer_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/transfers/{transfer_id}",
        headers=transfer_manager_headers,
    )

    assert response.status_code == 204

    center = db_session.get(
        RecyclingCenter, transfer_setup["center_id"]
    )
    assert center.available_capacity_kg == 1000


def test_unauthorized_transfer_access(client):
    response = client.get("/api/v1/transfers/")
    assert response.status_code == 401
