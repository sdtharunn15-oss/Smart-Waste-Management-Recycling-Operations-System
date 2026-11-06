def test_register_user_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": "customer@example.com",
            "phone": "9876543210",
            "password": "TestPass123"
        }
    )

    assert response.status_code == 201
    assert response.json()["email"] == "customer@example.com"


def test_register_duplicate_email(client):
    payload = {
        "full_name": "Test Customer",
        "email": "customer@example.com",
        "phone": "9876543210",
        "password": "TestPass123"
    }

    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": "invalid-email",
            "phone": "9876543210",
            "password": "TestPass123"
        }
    )

    assert response.status_code == 422


def test_register_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": "short@example.com",
            "phone": "9876543210",
            "password": "123"
        }
    )

    assert response.status_code == 422


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Login Customer",
            "email": "login@example.com",
            "phone": "9876543211",
            "password": "TestPass123"
        }
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPass123"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Login Customer",
            "email": "wrongpass@example.com",
            "phone": "9876543212",
            "password": "TestPass123"
        }
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPass123"
        }
    )

    assert response.status_code == 401


def test_refresh_token_success(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Refresh Customer",
            "email": "refresh@example.com",
            "phone": "9876543213",
            "password": "TestPass123"
        }
    )

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "TestPass123"
        }
    )

    refresh_token = login.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_invalid_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.value"}
    )

    assert response.status_code == 401