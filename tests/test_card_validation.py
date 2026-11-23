import pytest
from fastapi import HTTPException

from backend.standalone_user_api import card_brand, normalize_card_number


def test_card_number_is_luhn_validated_and_normalized():
    assert normalize_card_number("4111 1111 1111 1111") == "4111111111111111"
    assert card_brand("4111111111111111") == "visa"


def test_invalid_card_number_is_rejected():
    with pytest.raises(HTTPException):
        normalize_card_number("4111111111111112")
