import pytest
from datetime import date, timedelta

from app.utils.validators import (
    validate_positive_quantity,
    validate_non_negative_quantity,
    sanitize_text,
    validate_date_range,
    validate_positive_integer,
)


def test_positive_quantity():
    assert validate_positive_quantity(10) == 10


def test_positive_quantity_rejects_zero():
    with pytest.raises(ValueError):
        validate_positive_quantity(0)


def test_positive_quantity_rejects_negative():
    with pytest.raises(ValueError):
        validate_positive_quantity(-5)


def test_non_negative_quantity():
    assert validate_non_negative_quantity(0) == 0


def test_non_negative_quantity_rejects_negative():
    with pytest.raises(ValueError):
        validate_non_negative_quantity(-1)


def test_sanitize_text():
    assert sanitize_text("  Smart Waste  ") == "Smart Waste"


def test_sanitize_text_rejects_empty():
    with pytest.raises(ValueError):
        sanitize_text("   ")


def test_validate_date_range():
    today = date.today()
    assert validate_date_range(
        today,
        today + timedelta(days=1)
    )


def test_validate_positive_integer():
    assert validate_positive_integer(5) == 5


def test_validate_positive_integer_rejects_zero():
    with pytest.raises(ValueError):
        validate_positive_integer(0)