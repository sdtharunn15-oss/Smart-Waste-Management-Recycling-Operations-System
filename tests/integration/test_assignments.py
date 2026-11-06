
from datetime import date, timedelta

import pytest

from app.models.user import User
from app.models.location import Location
from app.models.customer import Customer
from app.models.waste_category import WasteCategory
from app.models.pickup_request import PickupRequest
from app.models.vehicle import Vehicle
from app.models.workforce import Workforce
from app.utils.enums import UserRole


@pytest.fixture
def management_headers(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Assignment Manager",
            "email": "assignment_manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000101",
        },
    )
    assert response.status_code == 201

    manager = db_session.query(User).filter(
        User.email == "assignment_manager@example.com"
    ).first()

    manager.role = UserRole.OPERATIONS_MANAGER.value
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "assignment_manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


@pytest.fixture
def assignment_setup(db_session):
    location = Location(
        name="Assignment Test Zone",
        code="ASN-ZONE",
        location_type="collection_zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Assignment Customer",
        email="assignment_customer@example.com",
        phone="9000000102",
        customer_type="residential",
        address="Test Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )

    category = WasteCategory(
        name="Assignment Recyclable",
        code="ASN-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    db_session.add_all([customer, category])
    db_session.flush()

    pickup = PickupRequest(
        request_number="ASN-PICKUP-001",
        customer_id=customer.id,
        location_id=location.id,
        waste_category_id=category.id,
        requested_date=date.today() + timedelta(days=2),
        estimated_quantity=100,
        quantity_unit="kg",
        pickup_address="Test Address, Chennai",
        priority="normal",
        status="approved",
    )

    vehicle = Vehicle(
        registration_number="TN-ASN-1001",
        vehicle_name="Assignment Truck",
        vehicle_type="truck",
        capacity_kg=500,
        fuel_type="diesel",
        status="available",
    )

    driver = Workforce(
        employee_code="ASN-DRIVER-01",
        full_name="Assignment Driver",
        phone="9000000103",
        role="driver",
        status="available",
        license_number="ASN-LICENSE-01",
    )

    db_session.add_all([pickup, vehicle, driver])
    db_session.commit()

    db_session.refresh(pickup)
    db_session.refresh(vehicle)
    db_session.refresh(driver)

    return {
        "pickup_request_id": pickup.id,
        "vehicle_id": vehicle.id,
        "driver_id": driver.id,
    }


def assignment_payload(setup):
    return {
        "pickup_request_id": setup["pickup_request_id"],
        "vehicle_id": setup["vehicle_id"],
        "driver_id": setup["driver_id"],
        "notes": "Test collection assignment",
    }


def test_create_assignment_success(
    client, management_headers, assignment_setup
):
    response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "assigned"
    assert data["pickup_request_id"] == assignment_setup["pickup_request_id"]
    assert data["vehicle_id"] == assignment_setup["vehicle_id"]
    assert data["driver_id"] == assignment_setup["driver_id"]
    assert data["assignment_number"].startswith("ASN-")


def test_assignment_rejects_unapproved_pickup(
    client, management_headers, assignment_setup, db_session
):
    pickup = db_session.get(
        PickupRequest, assignment_setup["pickup_request_id"]
    )
    pickup.status = "pending"
    db_session.commit()

    response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )

    assert response.status_code == 400


def test_assignment_rejects_unavailable_vehicle(
    client, management_headers, assignment_setup, db_session
):
    vehicle = db_session.get(
        Vehicle, assignment_setup["vehicle_id"]
    )
    vehicle.status = "maintenance"
    db_session.commit()

    response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )

    assert response.status_code == 400


def test_assignment_rejects_insufficient_vehicle_capacity(
    client, management_headers, assignment_setup, db_session
):
    vehicle = db_session.get(
        Vehicle, assignment_setup["vehicle_id"]
    )
    vehicle.capacity_kg = 50
    db_session.commit()

    response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )

    assert response.status_code == 400


def test_assignment_rejects_unavailable_driver(
    client, management_headers, assignment_setup, db_session
):
    driver = db_session.get(
        Workforce, assignment_setup["driver_id"]
    )
    driver.status = "on_leave"
    db_session.commit()

    response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )

    assert response.status_code == 400


def test_assignment_status_transition(
    client, management_headers, assignment_setup
):
    create_response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )
    assert create_response.status_code == 201

    assignment_id = create_response.json()["id"]

    start_response = client.patch(
        f"/api/v1/assignments/{assignment_id}/status",
        json={"status": "in_progress"},
        headers=management_headers,
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "in_progress"

    complete_response = client.patch(
        f"/api/v1/assignments/{assignment_id}/status",
        json={"status": "completed"},
        headers=management_headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_assignment_rejects_invalid_status_transition(
    client, management_headers, assignment_setup
):
    create_response = client.post(
        "/api/v1/assignments/",
        json=assignment_payload(assignment_setup),
        headers=management_headers,
    )
    assert create_response.status_code == 201

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/assignments/{assignment_id}/status",
        json={"status": "completed"},
        headers=management_headers,
    )

    assert response.status_code == 400


def test_get_nonexistent_assignment(client, management_headers):
    response = client.get(
        "/api/v1/assignments/99999",
        headers=management_headers,
    )

    assert response.status_code == 404


def test_unauthorized_assignment_access(client):
    response = client.get("/api/v1/assignments/")
    assert response.status_code == 401
