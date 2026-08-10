import unicodedata

import pytest
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace

from app.schemas.mapping import Gender
from evaluation.nemotron.transform import (
    RegionLabelIndexError,
    UnexpectedDistrictFormatError,
    UnexpectedSexValueError,
    build_seoul_label_to_code_index,
    district_to_region_code,
    sex_to_gender,
)

MZ = "http://mozip.ai/ontology#"
_MZ_NS = Namespace(MZ)

# 실제 mozip.owl에는 의존하지 않지만, "정확히 25개 자치구" 계약을 검증하려면
# fixture 자체도 25개를 갖춰야 한다. 앞 2개는 실제 코드와 동일하게(마포구,
# 강남구) 두고, 나머지는 합성 이름으로 채운다.
_VALID_25_DISTRICTS: list[tuple[str, str]] = [
    ("마포구", "SEOUL_MAPO"),
    ("강남구", "SEOUL_GANGNAM"),
] + [(f"자치구{i:02d}", f"SEOUL_TEST_{i:02d}") for i in range(3, 26)]


def _build_ontology_graph(districts: list[tuple[str | None, str]]) -> Graph:
    graph = Graph()
    graph.add((_MZ_NS.Region, RDF.type, OWL.Class))
    graph.add((_MZ_NS.partOf, RDF.type, OWL.ObjectProperty))
    graph.add((_MZ_NS.SEOUL, RDF.type, _MZ_NS.Region))
    graph.add((_MZ_NS.SEOUL, RDFS.label, Literal("서울특별시", lang="ko")))

    for label, code in districts:
        uri = _MZ_NS[code]
        graph.add((uri, RDF.type, _MZ_NS.Region))
        if label is not None:
            graph.add((uri, RDFS.label, Literal(label, lang="ko")))
        graph.add((uri, _MZ_NS.partOf, _MZ_NS.SEOUL))

    return graph


@pytest.fixture
def graph() -> Graph:
    return _build_ontology_graph(_VALID_25_DISTRICTS)


def test_sex_to_gender_maps_known_values():
    assert sex_to_gender("남자") == Gender.MALE
    assert sex_to_gender("여자") == Gender.FEMALE


def test_sex_to_gender_rejects_unexpected_value():
    with pytest.raises(UnexpectedSexValueError):
        sex_to_gender("남성")


def test_build_seoul_label_to_code_index_excludes_seoul_itself(graph):
    index = build_seoul_label_to_code_index(graph)

    assert len(index) == 25
    assert index["마포구"] == "SEOUL_MAPO"
    assert index["강남구"] == "SEOUL_GANGNAM"
    assert "서울특별시" not in index


def test_district_to_region_code_strips_prefix_and_looks_up_label(graph):
    index = build_seoul_label_to_code_index(graph)

    assert district_to_region_code("서울-마포구", index) == "SEOUL_MAPO"


def test_district_to_region_code_nfd_input_matches_nfc_label(graph):
    index = build_seoul_label_to_code_index(graph)
    nfd_district = unicodedata.normalize("NFD", "서울-마포구")

    assert district_to_region_code(nfd_district, index) == "SEOUL_MAPO"


def test_district_to_region_code_unknown_district_returns_none(graph):
    index = build_seoul_label_to_code_index(graph)

    assert district_to_region_code("서울-존재하지않는구", index) is None


def test_district_to_region_code_missing_prefix_raises(graph):
    index = build_seoul_label_to_code_index(graph)

    with pytest.raises(UnexpectedDistrictFormatError):
        district_to_region_code("마포구", index)


def test_district_to_region_code_empty_suffix_returns_none(graph):
    # "서울-"처럼 접두어만 있고 구 이름이 빈 문자열이면 임의로 추측하지 않고
    # 어떤 label과도 매치되지 않는 None(TRANSFORM_FAILED 경로)을 반환해야 한다.
    index = build_seoul_label_to_code_index(graph)

    assert district_to_region_code("서울-", index) is None


def test_build_seoul_label_to_code_index_raises_when_label_missing():
    districts = _VALID_25_DISTRICTS[:-1] + [(None, "SEOUL_TEST_25")]
    graph = _build_ontology_graph(districts)

    with pytest.raises(RegionLabelIndexError):
        build_seoul_label_to_code_index(graph)


def test_build_seoul_label_to_code_index_raises_when_label_duplicated():
    districts = _VALID_25_DISTRICTS[:-1] + [("마포구", "SEOUL_TEST_25")]
    graph = _build_ontology_graph(districts)

    with pytest.raises(RegionLabelIndexError):
        build_seoul_label_to_code_index(graph)


def test_build_seoul_label_to_code_index_raises_when_count_is_not_25():
    districts = _VALID_25_DISTRICTS[:-1]  # 24개

    graph = _build_ontology_graph(districts)

    with pytest.raises(RegionLabelIndexError):
        build_seoul_label_to_code_index(graph)
