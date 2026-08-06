from app.ontology.matcher import match_concepts
from app.schemas.mapping import (
    ConceptMapping,
    MappedConcept,
    MappingAxis,
    UnmappedField,
    UnmappedReason,
)

MZ = "http://mozip.ai/ontology#"


def _concept(field: MappingAxis, code: str) -> MappedConcept:
    return MappedConcept(field=field, concept_uri=f"{MZ}{code}", concept_code=code)


def test_no_common_evaluable_axes_returns_none_score():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score is None
    assert result.matched_concepts == []


def test_evaluable_axis_without_match_returns_zero():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "FEMALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []


def test_full_match_returns_one():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 2


def test_partial_match_returns_ratio():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
            _concept(MappingAxis.HOUSEHOLD_TYPE, "SINGLE"),
            _concept(MappingAxis.EMPLOYMENT_STATUS, "JOB_SEEKER"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
            _concept(MappingAxis.HOUSEHOLD_TYPE, "SINGLE"),
            _concept(MappingAxis.EMPLOYMENT_STATUS, "UNEMPLOYED"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 0.75


def test_score_rounds_to_four_decimal_places():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
            _concept(MappingAxis.HOUSEHOLD_TYPE, "SINGLE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "MEDIAN_PERCENTAGE"),
            _concept(MappingAxis.HOUSEHOLD_TYPE, "ELDERLY"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 0.3333


def test_policy_axis_with_multiple_concepts_counted_once():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.AGE_GROUP, "AGE_25_29")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.AGE_GROUP, "AGE_19_24"),
            _concept(MappingAxis.AGE_GROUP, "AGE_25_29"),
            _concept(MappingAxis.AGE_GROUP, "AGE_30_34"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "AGE_25_29"


def test_axis_with_unknown_value_still_evaluable_when_partially_mapped():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.EMPLOYMENT_STATUS, "JOB_SEEKER")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.EMPLOYMENT_STATUS, "JOB_SEEKER")],
        unmapped=[
            UnmappedField(
                field=MappingAxis.EMPLOYMENT_STATUS, reason=UnmappedReason.UNKNOWN_VALUE
            )
        ],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0


def test_axis_missing_on_one_side_is_excluded():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.AGE_GROUP, "AGE_25_29")],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[],
        unmapped=[UnmappedField(field=MappingAxis.AGE_GROUP, reason=UnmappedReason.MISSING_VALUE)],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score is None
    assert result.matched_concepts == []


def test_matched_concept_fields_populated_correctly():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping)

    matched = result.matched_concepts[0]
    assert matched.axis == MappingAxis.GENDER
    assert matched.user_concept_uri == f"{MZ}MALE"
    assert matched.user_concept_code == "MALE"
    assert matched.policy_concept_uri == f"{MZ}MALE"
    assert matched.policy_concept_code == "MALE"


def test_inference_paths_always_empty():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.inference_paths == []


def test_matched_concepts_follow_mapping_axis_declaration_order():
    # 입력 순서를 선언 순서와 다르게 뒤섞어도 결과는 MappingAxis 선언 순서를 따라야 한다.
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.AGE_GROUP, "AGE_25_29"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.AGE_GROUP, "AGE_25_29"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert [m.axis for m in result.matched_concepts] == [
        MappingAxis.GENDER,
        MappingAxis.AGE_GROUP,
        MappingAxis.INCOME_TYPE,
    ]


def test_duplicate_user_concept_yields_single_matched_pair():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].user_concept_code == "MALE"
    assert result.matched_concepts[0].policy_concept_code == "MALE"


def test_duplicate_policy_concept_yields_single_matched_pair():
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].user_concept_code == "MALE"
    assert result.matched_concepts[0].policy_concept_code == "MALE"


def test_duplicate_concepts_on_both_sides_yield_single_matched_pair():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1


def test_duplicate_concepts_do_not_affect_other_axes_score():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "ABSOLUTE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.INCOME_TYPE, "MEDIAN_PERCENTAGE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping)

    # 평가 가능 축 2개(gender, income_type) 중 gender만 매치 -> 0.5
    assert result.semantic_score == 0.5
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].axis == MappingAxis.GENDER


def test_match_concepts_is_deterministic():
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.AGE_GROUP, "AGE_25_29"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.GENDER, "MALE"),
            _concept(MappingAxis.AGE_GROUP, "AGE_25_29"),
        ],
        unmapped=[],
    )

    first = match_concepts(user_mapping, policy_mapping)
    second = match_concepts(user_mapping, policy_mapping)

    assert first == second
    assert [m.axis for m in first.matched_concepts] == [m.axis for m in second.matched_concepts]
