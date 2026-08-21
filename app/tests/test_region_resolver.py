import pytest

from app.ontology.loader import _load_graph
from app.ontology.region_resolver import resolve_region

FIXTURE_PATH = "app/tests/fixtures/test_region_resolver_ontology.ttl"
PRODUCTION_ONTOLOGY_PATH = "app/ontology/mozip.owl"


@pytest.fixture
def graph():
    return _load_graph(FIXTURE_PATH)


def test_exact_label_match_resolves(graph):
    assert resolve_region("강남구", graph) == "SEOUL_GANGNAM"


def test_two_syllable_stem_with_gu_omitted_resolves(graph):
    assert resolve_region("강남", graph) == "SEOUL_GANGNAM"


def test_one_syllable_stem_does_not_resolve(graph):
    assert resolve_region("중", graph) is None


def test_one_syllable_stem_exact_match_still_resolves(graph):
    assert resolve_region("중구", graph) == "SEOUL_JUNG"


@pytest.mark.parametrize("expression", ["서울", "서울시"])
def test_seoul_alias_resolves(graph, expression):
    assert resolve_region(expression, graph) == "SEOUL"


def test_unknown_region_does_not_resolve(graph):
    assert resolve_region("제주", graph) is None


@pytest.fixture(scope="module")
def production_graph():
    return _load_graph(PRODUCTION_ONTOLOGY_PATH)


def test_production_ontology_two_syllable_stem_resolves(production_graph):
    assert resolve_region("강남", production_graph) == "SEOUL_GANGNAM"


def test_production_ontology_one_syllable_stem_does_not_resolve(production_graph):
    assert resolve_region("중", production_graph) is None
