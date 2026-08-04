import pytest
from rdflib import Graph

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph, get_ontology_graph

FIXTURE_PATH = "app/tests/fixtures/test_ontology.ttl"


def test_load_graph_parses_valid_file():
    graph = _load_graph(FIXTURE_PATH)

    assert isinstance(graph, Graph)
    assert len(graph) > 0


def test_load_graph_raises_on_missing_file():
    with pytest.raises(AppException) as exc_info:
        _load_graph("app/tests/fixtures/does-not-exist.ttl")

    assert exc_info.value.code == "ONTOLOGY_FILE_NOT_FOUND"


def test_load_graph_raises_on_invalid_syntax(tmp_path):
    bad_file = tmp_path / "broken.ttl"
    bad_file.write_text("this is not valid turtle @@@ ###")

    with pytest.raises(AppException) as exc_info:
        _load_graph(str(bad_file))

    assert exc_info.value.code == "ONTOLOGY_LOAD_FAILED"


def test_get_ontology_graph_is_cached():
    get_ontology_graph.cache_clear()

    first = get_ontology_graph()
    second = get_ontology_graph()

    assert first is second
