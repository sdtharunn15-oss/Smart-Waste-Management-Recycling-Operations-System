import pytest
from uuid import uuid4

from app.main import app as fastapi_app
from app.core.dependencies import get_current_user
from app.models.customer import Customer
from app.models.user import User
from app.models.complaint import CustomerComplaint
from app.utils.enums import (
    ComplaintCategory,
    ComplaintPriority,
    ComplaintStatus,
)


def create_customer(db_session):
    customer = Customer(
        full_name="Test Customer",
        email=f"customer-{uuid4().hex[:8]}@example.com",
        phone=str(9000000000 + int(uuid4().hex[:8], 16) % 99999999),
        customer_type="residential",
        address="Test Street",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        status="active",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def create_user(db_session):
    user = User(
        full_name="Test Manager",
        email=f"manager-{uuid4().hex[:8]}@example.com",
        hashed_password="test-password",
        role="operations_manager",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def management_client(client, db_session):
    manager = create_user(db_session)

    fastapi_app.dependency_overrides[get_current_user] = (
        lambda: manager
    )

    return client


def create_complaint(db_session, customer):
    complaint = CustomerComplaint(
        complaint_number=f"CMP-{uuid4().hex[:12].upper()}",
        customer_id=customer.id,
        category=ComplaintCategory.MISSED_PICKUP,
        priority=ComplaintPriority.NORMAL,
        subject="Missed waste pickup",
        description="Waste was not collected on the scheduled date.",
        status=ComplaintStatus.OPEN,
    )
    db_session.add(complaint)
    db_session.commit()
    db_session.refresh(complaint)
    return complaint


def test_create_complaint(management_client, db_session):
    customer = create_customer(db_session)

    response = management_client.post(
        "/api/v1/complaints/",
        json={
            "customer_id": customer.id,
            "category": "missed_pickup",
            "priority": "normal",
            "subject": "Missed waste pickup",
            "description": "Waste was not collected on the scheduled date.",
        },
    )

    assert response.status_code == 201
    assert response.json()["customer_id"] == customer.id
    assert response.json()["status"] == "open"
    assert response.json()["complaint_number"].startswith("CMP-")


def test_create_complaint_invalid_customer(
    management_client,
):
    response = management_client.post(
        "/api/v1/complaints/",
        json={
            "customer_id": 99999,
            "category": "missed_pickup",
            "priority": "normal",
            "subject": "Missed waste pickup",
            "description": "Waste was not collected on the scheduled date.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Customer not found"


def test_create_complaint_invalid_category(
    management_client,
    db_session,
):
    customer = create_customer(db_session)

    response = management_client.post(
        "/api/v1/complaints/",
        json={
            "customer_id": customer.id,
            "category": "invalid_category",
            "priority": "normal",
            "subject": "Missed waste pickup",
            "description": "Waste was not collected on the scheduled date.",
        },
    )

    assert response.status_code == 422


def test_list_complaints(management_client, db_session):
    customer = create_customer(db_session)
    create_complaint(db_session, customer)

    response = management_client.get("/api/v1/complaints/")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["complaints"]) == 1


def test_get_complaint_not_found(management_client):
    response = management_client.get(
        "/api/v1/complaints/99999"
    )

    assert response.status_code == 404


def test_update_complaint(management_client, db_session):
    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    response = management_client.patch(
        f"/api/v1/complaints/{complaint.id}",
        json={"subject": "Updated complaint subject"},
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Updated complaint subject"


def test_assign_complaint(management_client, db_session):
    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)
    user = create_user(db_session)

    response = management_client.patch(
        f"/api/v1/complaints/{complaint.id}/assign",
        json={"assigned_to": user.id},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] == user.id
    assert response.json()["status"] == "assigned"


def test_resolve_complaint_requires_notes(db_session):
    from app.services.complaints import update_complaint_status

    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    complaint.status = ComplaintStatus.IN_PROGRESS
    db_session.commit()

    with pytest.raises(
        ValueError,
        match="Resolution notes are required",
    ):
        update_complaint_status(
            db_session,
            complaint.id,
            ComplaintStatus.RESOLVED,
        )


def test_complaint_status_transition(db_session):
    from app.services.complaints import update_complaint_status

    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    complaint.status = ComplaintStatus.IN_PROGRESS
    db_session.commit()

    updated = update_complaint_status(
        db_session,
        complaint.id,
        ComplaintStatus.RESOLVED,
        "Waste collection issue resolved.",
    )

    assert updated.status == ComplaintStatus.RESOLVED
    assert updated.resolution_notes == "Waste collection issue resolved."
    assert updated.resolved_at is not None


def test_invalid_complaint_status_transition(db_session):
    from app.services.complaints import update_complaint_status

    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    with pytest.raises(
        ValueError,
        match="Cannot change complaint status",
    ):
        update_complaint_status(
            db_session,
            complaint.id,
            ComplaintStatus.CLOSED,
        )


def test_delete_open_complaint(db_session):
    from app.services.complaints import remove_complaint

    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    assert remove_complaint(db_session, complaint.id) is True

    assert (
        db_session.query(CustomerComplaint)
        .filter(CustomerComplaint.id == complaint.id)
        .first()
        is None
    )


def test_delete_assigned_complaint_not_allowed(db_session):
    from app.services.complaints import remove_complaint

    customer = create_customer(db_session)
    complaint = create_complaint(db_session, customer)

    complaint.status = ComplaintStatus.ASSIGNED
    db_session.commit()

    with pytest.raises(
        ValueError,
        match="Only open or rejected",
    ):
        remove_complaint(db_session, complaint.id)


def test_complaints_require_authentication(client):
    response = client.get("/api/v1/complaints/")

    assert response.status_code == 401