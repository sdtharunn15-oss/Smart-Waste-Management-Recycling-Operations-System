import pytest
import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hash_is_generated():
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)


def test_password_verification_success():
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_password_verification_failure():
    hashed = hash_password("SecurePassword123!")

    assert verify_password("WrongPassword123!", hashed) is False


def test_access_token_creation():
    token = create_access_token(1, "super_admin")

    assert isinstance(token, str)
    assert len(token) > 20


def test_access_token_decoding():
    token = create_access_token(1, "super_admin")
    payload = decode_token(token)

    assert payload["sub"] == "1"
    assert payload["role"] == "super_admin"
    assert payload["type"] == "access"


def test_refresh_token_creation():
    token = create_refresh_token(1)

    assert isinstance(token, str)


def test_refresh_token_decoding():
    token = create_refresh_token(1)
    payload = decode_token(token)

    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"


def test_invalid_token_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("invalid.token.value")