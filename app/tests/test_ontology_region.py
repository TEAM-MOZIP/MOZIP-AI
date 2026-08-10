import re
from pathlib import Path

import pytest
from rdflib import Namespace

from app.ontology.graph import get_individuals, get_related
from app.ontology.loader import _load_graph

MZ = Namespace("http://mozip.ai/ontology#")
PRODUCTION_ONTOLOGY_PATH = "app/ontology/mozip.owl"
REGION_CONTRACT_PATH = Path("docs/ai-integration/region-contract.md")

# region-contract.md의 26개 Region code 표(`| 구분 | code | name |`)에서 code 열만 읽어온다.
# 운영 mozip.owl과 대조할 때 26개 code를 테스트에 다시 하드코딩하지 않기 위함이다.
_CONTRACT_TABLE_ROW = re.compile(r"^\|[^|]+\|\s*`(SEOUL[A-Z_]*)`\s*\|", re.MULTILINE)


def _contract_region_codes() -> set[str]:
    text = REGION_CONTRACT_PATH.read_text(encoding="utf-8")
    codes = set(_CONTRACT_TABLE_ROW.findall(text))
    assert codes, "region-contract.md 표에서 Region code를 하나도 찾지 못했습니다."
    return codes


@pytest.fixture(scope="module")
def graph():
    return _load_graph(PRODUCTION_ONTOLOGY_PATH)


def test_region_individual_count_is_26(graph):
    individuals = get_individuals(graph, MZ.Region)
    assert len(individuals) == 26


def test_seoul_exists_and_has_no_part_of(graph):
    individuals = {str(uri) for uri in get_individuals(graph, MZ.Region)}
    assert str(MZ.SEOUL) in individuals
    assert get_related(graph, MZ.SEOUL, MZ.partOf) == []


def test_all_districts_have_exactly_one_part_of_seoul(graph):
    individuals = get_individuals(graph, MZ.Region)
    districts = [uri for uri in individuals if uri != MZ.SEOUL]

    assert len(districts) == 25
    for district in districts:
        assert get_related(graph, district, MZ.partOf) == [MZ.SEOUL]


def test_removed_dummy_regions_are_absent(graph):
    individuals = {str(uri) for uri in get_individuals(graph, MZ.Region)}
    for removed_code in ("GYEONGGI", "BUSAN", "INCHEON", "DAEGU"):
        assert str(MZ[removed_code]) not in individuals


@pytest.mark.skipif(
    not REGION_CONTRACT_PATH.exists(),
    reason="region-contract.md는 Git에 포함되지 않는 로컬 공유 계약 문서",
)
def test_ontology_region_codes_match_contract_document(graph):
    ontology_codes = {
        str(uri).removeprefix(str(MZ)) for uri in get_individuals(graph, MZ.Region)
    }
    assert ontology_codes == _contract_region_codes()
