import re
from collections.abc import Callable

from app.schemas.mapping import EmploymentStatus, Gender, HouseholdType, IncomeType

_GENDER_ALIASES: dict[str, Gender] = {
    "여성": Gender.FEMALE,
    "여자": Gender.FEMALE,
    "남성": Gender.MALE,
    "남자": Gender.MALE,
}

_EMPLOYMENT_STATUS_ALIASES: dict[str, EmploymentStatus] = {
    "취준생": EmploymentStatus.JOB_SEEKER,
    "구직자": EmploymentStatus.JOB_SEEKER,
    "무직": EmploymentStatus.UNEMPLOYED,
    "백수": EmploymentStatus.UNEMPLOYED,
    "직장인": EmploymentStatus.EMPLOYED,
    "재직중": EmploymentStatus.EMPLOYED,
}

_HOUSEHOLD_TYPE_ALIASES: dict[str, HouseholdType] = {
    "1인 가구": HouseholdType.SINGLE,
    "혼자 살아요": HouseholdType.SINGLE,
    "한부모": HouseholdType.SINGLE_PARENT,
    "한부모 가정": HouseholdType.SINGLE_PARENT,
    "노인 가구": HouseholdType.ELDERLY,
    "장애인 가구": HouseholdType.DISABLED,
}

# 순서대로 시도한다. "만 27세"가 "27세" 패턴에도 부분적으로 걸리지 않도록
# 전부 fullmatch로만 판정한다(partial match로 임의 canonicalize하지 않기 위함).
_AGE_PATTERNS = [
    re.compile(r"(\d+)살"),
    re.compile(r"만\s*(\d+)세"),
    re.compile(r"(\d+)세"),
]

_ABSOLUTE_INCOME_PATTERN = re.compile(r"월\s*소득\s*(\d+)\s*만원")
_MEDIAN_PERCENTAGE_PATTERN = re.compile(r"중위소득\s*(\d+)\s*%")


def resolve_gender(expression: str) -> Gender | None:
    return _GENDER_ALIASES.get(expression.strip())


def resolve_employment_status(expression: str) -> EmploymentStatus | None:
    return _EMPLOYMENT_STATUS_ALIASES.get(expression.strip())


def resolve_household_type(expression: str) -> HouseholdType | None:
    return _HOUSEHOLD_TYPE_ALIASES.get(expression.strip())


def resolve_age(expression: str) -> int | None:
    text = expression.strip()
    for pattern in _AGE_PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return int(match.group(1))
    return None


def resolve_income(expression: str) -> tuple[IncomeType, int] | None:
    text = expression.strip()

    match = _ABSOLUTE_INCOME_PATTERN.fullmatch(text)
    if match:
        return IncomeType.ABSOLUTE, int(match.group(1)) * 10000

    match = _MEDIAN_PERCENTAGE_PATTERN.fullmatch(text)
    if match:
        return IncomeType.MEDIAN_PERCENTAGE, int(match.group(1))

    return None


def resolve_axis[T](
    expressions: list[str], resolve_expression: Callable[[str], T | None]
) -> tuple[T | None, list[str]]:
    if not expressions:
        return None, []

    canonical_values = [resolve_expression(expression) for expression in expressions]
    unique_resolved = {value for value in canonical_values if value is not None}

    if len(unique_resolved) == 1 and all(value is not None for value in canonical_values):
        return next(iter(unique_resolved)), []

    return None, expressions
