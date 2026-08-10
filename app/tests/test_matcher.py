import pytest
from rdflib import Graph, URIRef

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


def _region_graph(*part_of_pairs: tuple[str, str]) -> Graph:
    # (child_code, parent_code) 쌍마다 child --PART_OF--> parent 트리플 하나를 추가한다.
    # 운영 mozip.owl이나 Mapper용 TTL fixture와 무관하게, Matcher가 "주어진 관계를
    # 1홉만 읽는가"만 검증하기 위한 최소 인라인 그래프다.
    graph = Graph()
    part_of = URIRef(f"{MZ}partOf")
    for child_code, parent_code in part_of_pairs:
        graph.add((URIRef(f"{MZ}{child_code}"), part_of, URIRef(f"{MZ}{parent_code}")))
    return graph


@pytest.fixture
def graph() -> Graph:
    return Graph()


def test_no_common_evaluable_axes_returns_none_score(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score is None
    assert result.matched_concepts == []


def test_evaluable_axis_without_match_returns_zero(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "FEMALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []


def test_full_match_returns_one(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 2


def test_partial_match_returns_ratio(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.75


def test_score_rounds_to_four_decimal_places(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.3333


def test_policy_axis_with_multiple_concepts_counted_once(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "AGE_25_29"


def test_axis_with_unknown_value_still_evaluable_when_partially_mapped(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0


def test_axis_missing_on_one_side_is_excluded(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.AGE_GROUP, "AGE_25_29")],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[],
        unmapped=[UnmappedField(field=MappingAxis.AGE_GROUP, reason=UnmappedReason.MISSING_VALUE)],
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score is None
    assert result.matched_concepts == []


def test_matched_concept_fields_populated_correctly(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    matched = result.matched_concepts[0]
    assert matched.axis == MappingAxis.GENDER
    assert matched.user_concept_uri == f"{MZ}MALE"
    assert matched.user_concept_code == "MALE"
    assert matched.policy_concept_uri == f"{MZ}MALE"
    assert matched.policy_concept_code == "MALE"


def test_inference_paths_always_empty(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.GENDER, "MALE")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.inference_paths == []


def test_matched_concepts_follow_mapping_axis_declaration_order(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert [m.axis for m in result.matched_concepts] == [
        MappingAxis.GENDER,
        MappingAxis.AGE_GROUP,
        MappingAxis.INCOME_TYPE,
    ]


def test_duplicate_user_concept_yields_single_matched_pair(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].user_concept_code == "MALE"
    assert result.matched_concepts[0].policy_concept_code == "MALE"


def test_duplicate_policy_concept_yields_single_matched_pair(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].user_concept_code == "MALE"
    assert result.matched_concepts[0].policy_concept_code == "MALE"


def test_duplicate_concepts_on_both_sides_yield_single_matched_pair(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1


def test_duplicate_concepts_do_not_affect_other_axes_score(graph):
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

    result = match_concepts(user_mapping, policy_mapping, graph)

    # 평가 가능 축 2개(gender, income_type) 중 gender만 매치 -> 0.5
    assert result.semantic_score == 0.5
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].axis == MappingAxis.GENDER


def test_match_concepts_is_deterministic(graph):
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

    first = match_concepts(user_mapping, policy_mapping, graph)
    second = match_concepts(user_mapping, policy_mapping, graph)

    assert first == second
    assert [m.axis for m in first.matched_concepts] == [m.axis for m in second.matched_concepts]


def test_region_exact_match_has_no_inference_path(graph):
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "SEOUL_MAPO"
    assert result.inference_paths == []


def test_region_partof_match_from_district_to_seoul():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    matched = result.matched_concepts[0]
    assert matched.axis == MappingAxis.REGION
    assert matched.user_concept_uri == f"{MZ}SEOUL_MAPO"
    assert matched.user_concept_code == "SEOUL_MAPO"
    assert matched.policy_concept_uri == f"{MZ}SEOUL"
    assert matched.policy_concept_code == "SEOUL"

    assert len(result.inference_paths) == 1
    path = result.inference_paths[0]
    assert path.axis == MappingAxis.REGION
    assert path.from_concept_uri == f"{MZ}SEOUL_MAPO"
    assert path.relations == ["PART_OF"]
    assert path.to_concept_uri == f"{MZ}SEOUL"


def test_region_different_districts_not_matched():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"), ("SEOUL_SONGPA", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_SONGPA")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []
    assert result.inference_paths == []


def test_region_reverse_direction_not_matched():
    # 부모(SEOUL)가 사용자이고 자치구가 정책인 반대 방향은 PART_OF 매치로 인정하지 않는다.
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []
    assert result.inference_paths == []


def test_non_region_axis_ignores_part_of_relation():
    # EMPLOYMENT_STATUS 축에 PART_OF와 동일한 형태의 관계 트리플이 있어도,
    # PART_OF 간접 매칭은 REGION 축에만 적용되어야 한다.
    graph = _region_graph(("EMPLOYED", "JOB_SEEKER"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.EMPLOYMENT_STATUS, "EMPLOYED")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.EMPLOYMENT_STATUS, "JOB_SEEKER")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []
    assert result.inference_paths == []


def test_region_exact_takes_priority_over_part_of():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
            _concept(MappingAxis.REGION, "SEOUL"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "SEOUL_MAPO"
    assert result.inference_paths == []


def test_region_partof_matches_one_of_multiple_policy_regions():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_SONGPA"),
            _concept(MappingAxis.REGION, "SEOUL"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "SEOUL"


def test_region_multiple_part_of_matches_still_count_axis_once():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"), ("SEOUL_MAPO", "CAPITAL_AREA"))
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
            _concept(MappingAxis.GENDER, "MALE"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL"),
            _concept(MappingAxis.REGION, "CAPITAL_AREA"),
            _concept(MappingAxis.GENDER, "FEMALE"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    # 평가 가능 축 2개(region, gender) 중 region만 매치 -> 0.5. region 축 안에서는
    # PART_OF 쌍이 2개(SEOUL, CAPITAL_AREA) 성립하지만 축 점수는 1회만 반영된다.
    assert result.semantic_score == 0.5
    region_matches = [m for m in result.matched_concepts if m.axis == MappingAxis.REGION]
    assert len(region_matches) == 2
    assert {m.policy_concept_code for m in region_matches} == {"SEOUL", "CAPITAL_AREA"}


def test_region_two_hop_relation_is_not_followed():
    # LEAF -> MID -> TOP은 실제 서비스에는 없는 가상의 3단계 예시로, 1홉만 지원한다는
    # 계약을 회귀 테스트로 고정하기 위한 용도다.
    graph = _region_graph(("LEAF", "MID"), ("MID", "TOP"))
    user_mapping = ConceptMapping(concepts=[_concept(MappingAxis.REGION, "LEAF")], unmapped=[])
    policy_mapping = ConceptMapping(concepts=[_concept(MappingAxis.REGION, "TOP")], unmapped=[])

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 0.0
    assert result.matched_concepts == []
    assert result.inference_paths == []


def test_region_partof_match_is_deterministic():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL_MAPO")], unmapped=[]
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )

    first = match_concepts(user_mapping, policy_mapping, graph)
    second = match_concepts(user_mapping, policy_mapping, graph)

    assert first == second


def test_region_duplicate_user_concept_with_partof_yields_single_pair():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[_concept(MappingAxis.REGION, "SEOUL")], unmapped=[]
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "SEOUL"
    assert len(result.inference_paths) == 1
    assert result.inference_paths[0].to_concept_uri == f"{MZ}SEOUL"


def test_region_duplicate_user_concept_with_exact_and_partof_mixed():
    graph = _region_graph(("SEOUL_MAPO", "SEOUL"))
    user_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
        ],
        unmapped=[],
    )
    policy_mapping = ConceptMapping(
        concepts=[
            _concept(MappingAxis.REGION, "SEOUL_MAPO"),
            _concept(MappingAxis.REGION, "SEOUL"),
        ],
        unmapped=[],
    )

    result = match_concepts(user_mapping, policy_mapping, graph)

    assert result.semantic_score == 1.0
    assert len(result.matched_concepts) == 1
    assert result.matched_concepts[0].policy_concept_code == "SEOUL_MAPO"
    assert result.inference_paths == []
