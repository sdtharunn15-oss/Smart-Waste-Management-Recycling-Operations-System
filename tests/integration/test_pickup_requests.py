
from datetime import date, timedelta

import pytest

from app.models.customer import Customer
from app.models.location import Location
from app.models.waste_category import WasteCategory
from app.models.user import User
from app.utils.enums import UserRole


@pytest.fixture
def management_headers(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Manager",
            "email": "manager@example.com",
            "password": "TestPassword123",
            "phone": "9000000001",
        },
    )
    assert register_response.status_code == 201

    # Change the registered user's role to operations_manager.
    from app.main import app as fastapi_app
    from app.db.session import get_db

    db_override = fastapi_app.dependency_overrides[get_db]
    db = next(db_override())
    try:
        manager = db.query(User).filter(
            User.email == "manager@example.com"
        ).first()
        manager.role = UserRole.OPERATIONS_MANAGER.value
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "TestPassword123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pickup_setup(db_session):
    location = Location(
        name="Test Collection Zone",
        code="TEST-ZONE",
        location_type="zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    customer = Customer(
        full_name="Test Customer",
        email="customer@example.com",
        phone="9000000002",
        customer_type="residential",
        address="Test Customer Address",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        location_id=location.id,
        status="active",
    )
    category = WasteCategory(
        name="Test Recyclable",
        code="TEST-REC",
        waste_type="recyclable",
        is_recyclable=True,
        default_unit="kg",
        status="active",
    )

    db_session.add_all([customer, category])
    db_session.commit()
    db_session.refresh(location)
    db_session.refresh(customer)
    db_session.refresh(category)

    return {
        "location_id": location.id,
        "customer_id": customer.id,
        "waste_category_id": category.id,
    }


def valid_payload(setup):
    return {
        **setup,
        "requested_date": (date.today() + timedelta(days=2)).isoformat(),
        "estimated_quantity": 25,
        "quantity_unit": "KG",
        "pickup_address": "Test Customer Address, Chennai",
        "priority": "normal",
    }


def test_create_pickup_request_success(
    client, management_headers, pickup_setup
):
    response = client.post(
        "/api/v1/pickup-requests/",
        json=valid_payload(pickup_setup),
        headers=management_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["estimated_quantity"] == 25
    assert data["quantity_unit"] == "kg"
    assert data["request_number"].startswith("SWM-")


def test_create_pickup_request_invalid_customer(
    client, management_headers, pickup_setup
):
    payload = valid_payload(pickup_setup)
    payload["customer_id"] = 99999

    response = client.post(
        "/api/v1/pickup-requests/",
        json=payload,
        headers=management_headers,
    )

    assert response.status_code == 404


def test_create_pickup_request_location_mismatch(
    client, management_headers, pickup_setup, db_session
):
    other_location = Location(
        name="Other Zone",
        code="OTHER-ZONE",
        location_type="zone",
        city="Chennai",
        state="Tamil Nadu",
        status="active",
    )
    db_session.add(other_location)
    db_session.commit()
    db_session.refresh(other_location)

    payload = valid_payload(pickup_setup)
    payload["location_id"] = other_location.id

    response = client.post(
        "/api/v1/pickup-requests/",
        json=payload,
        headers=management_headers,
    )

    assert response.status_code == 400


def test_create_pickup_request_past_date(
    client, management_headers, pickup_setup
):
    payload = valid_payload(pickup_setup)
    payload["requested_date"] = (
        date.today() - timedelta(days=1)
    ).isoformat()

    response = client.post(
        "/api/v1/pickup-requests/",
        json=payload,
        headers=management_headers,
    )

    assert response.status_code == 400


def test_create_pickup_request_zero_quantity(
    client, management_headers, pickup_setup
):
    payload = valid_payload(pickup_setup)
    payload["estimated_quantity"] = 0

    response = client.post(
        "/api/v1/pickup-requests/",
        json=payload,
        headers=management_headers,
    )

    assert response.status_code == 422


def test_list_pickup_requests(
    client, management_headers, pickup_setup
):
    client.post(
        "/api/v1/pickup-requests/",
        json=valid_payload(pickup_setup),
        headers=management_headers,
    )

    response = client.get(
        "/api/v1/pickup-requests/",
        headers=management_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["requests"]) == 1


def test_get_nonexistent_pickup_request(
    client, management_headers
):
    response = client.get(
        "/api/v1/pickup-requests/99999",
        headers=management_headers,
    )

    assert response.status_code == 404


def test_reject_request_requires_reason(
    client, management_headers, pickup_setup
):
    create_response = client.post(
        "/api/v1/pickup-requests/",
        json=valid_payload(pickup_setup),
        headers=management_headers,
    )
    request_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/pickup-requests/{request_id}/status",
        json={"status": "rejected"},
        headers=management_headers,
    )

    assert response.status_code == 400


def test_cancel_pickup_request(
    client, management_headers, pickup_setup
):
    create_response = client.post(
        "/api/v1/pickup-requests/",
        json=valid_payload(pickup_setup),
        headers=management_headers,
    )
    request_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/pickup-requests/{request_id}/cancel",
        headers=management_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_unauthorized_pickup_request_access(client):
    response = client.get("/api/v1/pickup-requests/")
    assert response.status_code == 401
