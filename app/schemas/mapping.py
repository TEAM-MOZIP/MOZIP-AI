from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class EmploymentStatus(StrEnum):
    EMPLOYED = "EMPLOYED"
    UNEMPLOYED = "UNEMPLOYED"
    JOB_SEEKER = "JOB_SEEKER"


class HouseholdType(StrEnum):
    SINGLE = "SINGLE"
    ELDERLY = "ELDERLY"
    SINGLE_PARENT = "SINGLE_PARENT"
    DISABLED = "DISABLED"


class IncomeType(StrEnum):
    ABSOLUTE = "ABSOLUTE"
    MEDIAN_PERCENTAGE = "MEDIAN_PERCENTAGE"


class UserMappingInput(BaseModel):
    gender: Gender
    birth_date: date | None = None
    region_code: str | None = None
    employment_status: EmploymentStatus | None = None
    household_type: HouseholdType | None = None
    income_type: IncomeType | None = None


class UnmappedReason(StrEnum):
    MISSING_VALUE = "MISSING_VALUE"
    UNKNOWN_VALUE = "UNKNOWN_VALUE"


class MappedConcept(BaseModel):
    field: str
    concept_uri: str
    concept_code: str


class UnmappedField(BaseModel):
    field: str
    reason: UnmappedReason


class UserConceptMapping(BaseModel):
    concepts: list[MappedConcept]
    unmapped: list[UnmappedField]
