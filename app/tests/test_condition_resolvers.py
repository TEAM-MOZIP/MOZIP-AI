import pytest

from app.schemas.mapping import EmploymentStatus, Gender, HouseholdType, IncomeType
from app.services.condition_resolvers import (
    resolve_age,
    resolve_axis,
    resolve_employment_status,
    resolve_gender,
    resolve_household_type,
    resolve_income,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("여성", Gender.FEMALE),
        ("여자", Gender.FEMALE),
        ("남성", Gender.MALE),
        ("남자", Gender.MALE),
        ("사람", None),
    ],
)
def test_resolve_gender(expression, expected):
    assert resolve_gender(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("취준생", EmploymentStatus.JOB_SEEKER),
        ("구직자", EmploymentStatus.JOB_SEEKER),
        ("무직", EmploymentStatus.UNEMPLOYED),
        ("백수", EmploymentStatus.UNEMPLOYED),
        ("직장인", EmploymentStatus.EMPLOYED),
        ("재직중", EmploymentStatus.EMPLOYED),
        ("프리랜서", None),
        ("자영업자", None),
        ("계약직", None),
    ],
)
def test_resolve_employment_status(expression, expected):
    assert resolve_employment_status(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1인 가구", HouseholdType.SINGLE),
        ("혼자 살아요", HouseholdType.SINGLE),
        ("한부모", HouseholdType.SINGLE_PARENT),
        ("한부모 가정", HouseholdType.SINGLE_PARENT),
        ("노인 가구", HouseholdType.ELDERLY),
        ("장애인 가구", HouseholdType.DISABLED),
        ("저는 노인이에요", None),
        ("저는 장애인이에요", None),
        ("부모님이 노인이세요", None),
    ],
)
def test_resolve_household_type(expression, expected):
    assert resolve_household_type(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("25살", 25),
        ("만 27세", 27),
        ("27세", 27),
        ("저 25인데요", None),
        ("25살이에요", None),
        ("청년", None),
        ("20대", None),
        ("사회초년생", None),
        ("2001년생", None),
    ],
)
def test_resolve_age(expression, expected):
    assert resolve_age(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("월 소득 200만원", (IncomeType.ABSOLUTE, 2000000)),
        ("월소득 200만원", (IncomeType.ABSOLUTE, 2000000)),
        ("월 소득 200 만원", (IncomeType.ABSOLUTE, 2000000)),
        ("중위소득 100%", (IncomeType.MEDIAN_PERCENTAGE, 100)),
        ("연봉 3000만원", None),
        ("소득 200만원", None),
        ("중위소득 기준이에요", None),
        ("월 소득 200만원입니다", None),
    ],
)
def test_resolve_income(expression, expected):
    assert resolve_income(expression) == expected


def test_resolve_axis_returns_missing_when_no_expressions():
    assert resolve_axis([], resolve_gender) == (None, [])


def test_resolve_axis_resolves_single_expression():
    assert resolve_axis(["여성"], resolve_gender) == (Gender.FEMALE, [])


def test_resolve_axis_resolves_when_expressions_share_canonical_value():
    assert resolve_axis(["여자", "여성"], resolve_gender) == (Gender.FEMALE, [])


def test_resolve_axis_keeps_unresolved_when_canonical_values_conflict():
    expressions = ["직장인", "취준생"]
    assert resolve_axis(expressions, resolve_employment_status) == (None, expressions)


def test_resolve_axis_keeps_unresolved_when_one_expression_fails_to_resolve():
    expressions = ["취준생", "프리랜서"]
    assert resolve_axis(expressions, resolve_employment_status) == (None, expressions)


def test_resolve_axis_preserves_original_order():
    expressions = ["프리랜서", "취준생"]
    _, unresolved = resolve_axis(expressions, resolve_employment_status)
    assert unresolved == expressions
