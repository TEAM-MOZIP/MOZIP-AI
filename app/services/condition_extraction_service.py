from rdflib import Graph

from app.clients.llm_client import LlmClient
from app.core.exceptions import AppException
from app.ontology.region_resolver import resolve_region
from app.prompts.condition_extraction import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.condition_extraction import (
    ConditionAxis,
    ConditionExtractionRequest,
    ConditionExtractionResponse,
    UnresolvedCondition,
    _ConditionExpressions,
)
from app.services.condition_resolvers import (
    resolve_age,
    resolve_axis,
    resolve_employment_status,
    resolve_gender,
    resolve_household_type,
    resolve_income,
)


def _assert_expressions_are_verbatim_substrings(
    expressions: _ConditionExpressions, free_text: str
) -> None:
    all_expressions = (
        expressions.gender_expressions
        + expressions.age_expressions
        + expressions.region_expressions
        + expressions.employment_status_expressions
        + expressions.household_type_expressions
        + expressions.income_expressions
    )
    for expression in all_expressions:
        stripped = expression.strip()
        if not stripped or stripped not in free_text:
            raise AppException(
                "LLM이 추출한 표현이 입력 원문에 없습니다.",
                code="INTERNAL_ERROR",
                status_code=500,
            )


def extract_conditions(
    request: ConditionExtractionRequest, llm_client: LlmClient, graph: Graph
) -> ConditionExtractionResponse:
    expressions = llm_client.generate_structured(
        SYSTEM_INSTRUCTION, build_user_content(request.free_text), _ConditionExpressions
    )

    _assert_expressions_are_verbatim_substrings(expressions, request.free_text)

    unresolved: list[UnresolvedCondition] = []

    gender, raw = resolve_axis(expressions.gender_expressions, resolve_gender)
    unresolved += [UnresolvedCondition(axis=ConditionAxis.GENDER, raw_text=r) for r in raw]

    age, raw = resolve_axis(expressions.age_expressions, resolve_age)
    unresolved += [UnresolvedCondition(axis=ConditionAxis.AGE, raw_text=r) for r in raw]

    region_code, raw = resolve_axis(
        expressions.region_expressions, lambda expression: resolve_region(expression, graph)
    )
    unresolved += [UnresolvedCondition(axis=ConditionAxis.REGION, raw_text=r) for r in raw]

    employment_status, raw = resolve_axis(
        expressions.employment_status_expressions, resolve_employment_status
    )
    unresolved += [
        UnresolvedCondition(axis=ConditionAxis.EMPLOYMENT_STATUS, raw_text=r) for r in raw
    ]

    household_type, raw = resolve_axis(
        expressions.household_type_expressions, resolve_household_type
    )
    unresolved += [UnresolvedCondition(axis=ConditionAxis.HOUSEHOLD_TYPE, raw_text=r) for r in raw]

    income, raw = resolve_axis(expressions.income_expressions, resolve_income)
    income_type, income_value = income if income is not None else (None, None)
    unresolved += [UnresolvedCondition(axis=ConditionAxis.INCOME, raw_text=r) for r in raw]

    return ConditionExtractionResponse(
        gender=gender,
        age=age,
        region_code=region_code,
        employment_status=employment_status,
        household_type=household_type,
        income_type=income_type,
        income_value=income_value,
        unresolved_conditions=unresolved,
    )
