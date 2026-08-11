import pytest
from rdflib import Graph

from app.ontology.age_group import age_group_name
from evaluation.nemotron.coverage_report import (
    EvaluationStatus,
    RowResult,
    build_report,
    evaluate_persona,
)
from evaluation.nemotron.sampling import SampledPersona

MZ = "http://mozip.ai/ontology#"

_MINIMAL_ONTOLOGY_TTL = f"""
@prefix mz: <{MZ}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

mz:Region a owl:Class .
mz:Gender a owl:Class .
mz:partOf a owl:ObjectProperty .

mz:MALE a mz:Gender .
mz:FEMALE a mz:Gender .

mz:SEOUL a mz:Region ; rdfs:label "서울특별시"@ko .
mz:SEOUL_MAPO a mz:Region ; rdfs:label "마포구"@ko ; mz:partOf mz:SEOUL .
"""


@pytest.fixture
def graph() -> Graph:
    graph = Graph()
    graph.parse(data=_MINIMAL_ONTOLOGY_TTL, format="turtle")
    return graph


@pytest.fixture
def label_to_code() -> dict[str, str]:
    # build_seoul_label_to_code_index() 자체의 검증 규칙(정확히 25개 등)은
    # test_transform.py에서 별도로 다루므로, 여기서는 evaluate_persona()가
    # 받는 dict 형태만 재현한 최소 고정값을 직접 준다.
    return {"마포구": "SEOUL_MAPO"}


def test_evaluate_persona_maps_known_district(graph, label_to_code):
    persona = SampledPersona(sex="남자", age=27, district="서울-마포구")

    result = evaluate_persona(persona, graph, label_to_code)

    assert result.gender_status == EvaluationStatus.MAPPED
    assert result.region_status == EvaluationStatus.MAPPED
    assert result.age_group_band == "AGE_25_29"


def test_evaluate_persona_unrecognized_district_is_transform_failed(graph, label_to_code):
    persona = SampledPersona(sex="여자", age=40, district="서울-존재하지않는구")

    result = evaluate_persona(persona, graph, label_to_code)

    assert result.region_status == EvaluationStatus.TRANSFORM_FAILED
    # gender는 district 변환 실패와 무관하게 여전히 평가된다.
    assert result.gender_status == EvaluationStatus.MAPPED


def test_evaluate_persona_age_group_reuses_shared_function(graph, label_to_code):
    persona = SampledPersona(sex="남자", age=52, district="서울-마포구")

    result = evaluate_persona(persona, graph, label_to_code)

    assert result.age_group_band == age_group_name(52)


def test_build_report_aggregates_counts_and_rates():
    results = [
        _row("서울-마포구", EvaluationStatus.MAPPED, EvaluationStatus.MAPPED, "AGE_25_29"),
        _row(
            "서울-존재하지않는구",
            EvaluationStatus.MAPPED,
            EvaluationStatus.TRANSFORM_FAILED,
            "AGE_30_34",
        ),
    ]

    report = build_report(results)

    assert report["sampling"]["total"] == 2
    assert report["gender"]["mapped"] == 2
    assert report["gender"]["mapped_rate"] == 1.0
    assert report["region"]["mapped"] == 1
    assert report["region"]["transform_failed"] == 1
    assert report["region"]["mapped_rate"] == 0.5


def test_build_report_not_evaluated_axes_are_fixed_and_separate():
    results = [_row("서울-마포구", EvaluationStatus.MAPPED, EvaluationStatus.MAPPED, "AGE_25_29")]

    report = build_report(results)

    assert report["not_evaluated"] == ["employment_status", "household_type", "income_type"]
    # NOT_EVALUATED 축은 gender/region 집계 딕셔너리 어디에도 섞여 들어가지 않는다.
    assert "employment_status" not in report["gender"]
    assert "employment_status" not in report["region"]


def _row(district, gender_status, region_status, age_group_band):
    return RowResult(
        district=district,
        sex="남자",
        age=30,
        gender_status=gender_status,
        region_status=region_status,
        age_group_band=age_group_band,
    )
