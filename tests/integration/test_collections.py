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


@pytest.fixture
def collection_manager_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Collection Manager",
            "email": "collection_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000201",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "collection_manager@example.com"
    ).first()

    manager.role = "operations_manager"
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "collection_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def collection_setup(db_session):
    location = Location(
        name="Collection Test Zone",
        code="COL-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Collection Customer",
        email="collection_customer@example.com",
        phone="9000000202",
        customer_type="residential",
        address="Collection Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Collection Recyclable",
        code="COL-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    db_session.add_all([customer, category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="COL-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Collection Test Address, Chennai",
        priority="normal",
        status="in_progress",
    )

    vehicle = Vehicle(
        registration_number="TN-COL-2001",
        vehicle_name="Collection Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="on_route",
    )

    driver = Workforce(
        employee_code="COL-DRIVER-01",
        full_name="Collection Driver",
        phone="9000000203",
        role="driver",
        status="on_duty",
        license_number="COL-LICENSE-01",
    )

    db_session.add_all([pickup, vehicle, driver])
    db_session.flush()

    assignment = CollectionAssignment(
        assignment_number="COL-ASN-001",
        pickup_request_id=pickup.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )

    db_session.add(assignment)
    db_session.commit()

    db_session.refresh(assignment)

    return {
        "assignment_id": assignment.id,
        "vehicle_id": vehicle.id,
        "driver_id": driver.id,
        "pickup_request_id": pickup.id,
    }


def collection_payload(setup):
    return {
        "assignment_id": setup["assignment_id"],
        "collected_quantity": 80,
        "quantity_unit": "kg",
        "collection_address": "Collection Test Address, Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "notes": "Collection completed successfully",
    }


def test_create_collection_success(
    client, collection_manager_headers, collection_setup
):
    response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["assignment_id"] == collection_setup["assignment_id"]
    assert data["collected_quantity"] == 80
    assert data["quantity_unit"] == "kg"
    assert data["collection_number"].startswith("COL-")


def test_collection_completes_assignment_and_pickup(
    client, collection_manager_headers, collection_setup, db_session
):
    response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )

    assert response.status_code == 201

    assignment = db_session.get(
        CollectionAssignment, collection_setup["assignment_id"]
    )
    pickup = db_session.get(
        PickupRequest, collection_setup["pickup_request_id"]
    )

    assert assignment.status == "completed"
    assert pickup.status == "completed"


def test_collection_rejects_duplicate_record(
    client, collection_manager_headers, collection_setup
):
    first_response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )

    assert second_response.status_code == 409


def test_collection_rejects_assignment_not_in_progress(
    client, collection_manager_headers, collection_setup, db_session
):
    assignment = db_session.get(
        CollectionAssignment, collection_setup["assignment_id"]
    )
    assignment.status = "assigned"
    db_session.commit()

    response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )

    assert response.status_code == 400


def test_collection_rejects_quantity_above_vehicle_capacity(
    client, collection_manager_headers, collection_setup, db_session
):
    vehicle = db_session.get(
        Vehicle, collection_setup["vehicle_id"]
    )
    vehicle.capacity_kg = 50
    db_session.commit()

    response = client.post(
        "/api/v1/collections/",
        json=collection_payload(collection_setup),
        headers=collection_manager_headers,
    )

    assert response.status_code == 400


def test_collection_rejects_future_start_time(
    client, collection_manager_headers, collection_setup
):
    payload = collection_payload(collection_setup)
    payload["collection_started_at"] = (
        datetime.now(timezone.utc) + timedelta(days=1)
    ).isoformat()

    response = client.post(
        "/api/v1/collections/",
        json=payload,
        headers=collection_manager_headers,
    )

    assert response.status_code == 400


def test_get_nonexistent_collection(
    client, collection_manager_headers
):
    response = client.get(
        "/api/v1/collections/99999",
        headers=collection_manager_headers,
    )

    assert response.status_code == 404


def test_unauthorized_collection_access(client):
    response = client.get("/api/v1/collections/")
    assert response.status_code == 401