from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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


class RegionScope(StrEnum):
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"


class MappingAxis(StrEnum):
    GENDER = "gender"
    AGE_GROUP = "age_group"
    REGION = "region"
    EMPLOYMENT_STATUS = "employment_status"
    HOUSEHOLD_TYPE = "household_type"
    INCOME_TYPE = "income_type"


class UserMappingInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    gender: Gender
    birth_date: date | None = None
    region_code: str | None = None
    employment_status: EmploymentStatus | None = None
    household_type: HouseholdType | None = None
    income_type: IncomeType | None = None


class PolicyMappingInput(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    region_scope: RegionScope
    region_codes: list[str] = Field(default_factory=list)
    minimum_age: int | None = None
    maximum_age: int | None = None
    gender_condition: Gender | None = None
    income_type: IncomeType | None = None
    allowed_employment_statuses: list[str] = Field(default_factory=list)
    allowed_household_types: list[str] = Field(default_factory=list)


class UnmappedReason(StrEnum):
    MISSING_VALUE = "MISSING_VALUE"
    UNKNOWN_VALUE = "UNKNOWN_VALUE"


class MappedConcept(BaseModel):
    field: MappingAxis
    concept_uri: str
    concept_code: str


class UnmappedField(BaseModel):
    field: MappingAxis
    reason: UnmappedReason


class ConceptMapping(BaseModel):
    concepts: list[MappedConcept]
    unmapped: list[UnmappedField]
