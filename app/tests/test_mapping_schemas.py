import pytest
from pydantic import ValidationError

from app.schemas.mapping import UserMappingInput


def test_gender_is_required():
    with pytest.raises(ValidationError):
        UserMappingInput()


def test_minimal_valid_input_only_requires_gender():
    input_data = UserMappingInput(gender="MALE")

    assert input_data.gender == "MALE"
    assert input_data.birth_date is None
    assert input_data.region_code is None
    assert input_data.employment_status is None
    assert input_data.household_type is None
    assert input_data.income_type is None


def test_invalid_gender_value_rejected():
    with pytest.raises(ValidationError):
        UserMappingInput(gender="UNKNOWN")


def test_invalid_employment_status_value_rejected():
    with pytest.raises(ValidationError):
        UserMappingInput(gender="MALE", employment_status="RETIRED")


def test_invalid_household_type_value_rejected():
    with pytest.raises(ValidationError):
        UserMappingInput(gender="MALE", household_type="COUPLE")


def test_invalid_income_type_value_rejected():
    with pytest.raises(ValidationError):
        UserMappingInput(gender="MALE", income_type="RELATIVE")
