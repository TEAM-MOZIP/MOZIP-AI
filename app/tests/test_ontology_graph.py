import pytest
from rdflib import Namespace

from app.ontology.graph import (
    concept_exists,
    get_individuals,
    get_related,
    get_subclasses,
    get_superclasses,
    get_type,
)
from app.ontology.loader import _load_graph

TEST = Namespace("http://mozip.ai/test-ontology#")
FIXTURE_PATH = "app/tests/fixtures/test_ontology.ttl"


@pytest.fixture
def graph():
    return _load_graph(FIXTURE_PATH)


def test_concept_exists_true_for_known_concept(graph):
    assert concept_exists(graph, TEST.TestConcept) is True
    assert concept_exists(graph, TEST.ValueA) is True


def test_concept_exists_false_for_unknown_concept(graph):
    assert concept_exists(graph, TEST.NotDefined) is False


def test_get_type_returns_individuals_class(graph):
    assert get_type(graph, TEST.ValueA) == TEST.TestSubConcept


def test_get_superclasses_returns_direct_parent(graph):
    assert get_superclasses(graph, TEST.TestSubConcept) == [TEST.TestConcept]


def test_get_subclasses_returns_direct_children(graph):
    assert get_subclasses(graph, TEST.TestConcept) == [TEST.TestSubConcept]


def test_get_individuals_returns_instances_of_class(graph):
    individuals = set(get_individuals(graph, TEST.TestSubConcept))

    assert individuals == {TEST.ValueA, TEST.ValueB}


def test_get_related_follows_object_property(graph):
    assert get_related(graph, TEST.ValueA, TEST.relatedTo) == [TEST.ValueB]
