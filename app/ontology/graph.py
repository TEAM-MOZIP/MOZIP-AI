from rdflib import RDF, RDFS, Graph, URIRef


def concept_exists(graph: Graph, concept: URIRef) -> bool:
    return (concept, None, None) in graph or (None, None, concept) in graph


def get_type(graph: Graph, individual: URIRef) -> URIRef | None:
    return graph.value(individual, RDF.type)


def get_superclasses(graph: Graph, concept: URIRef) -> list[URIRef]:
    return list(graph.objects(concept, RDFS.subClassOf))


def get_subclasses(graph: Graph, concept: URIRef) -> list[URIRef]:
    return list(graph.subjects(RDFS.subClassOf, concept))


def get_individuals(graph: Graph, concept: URIRef) -> list[URIRef]:
    return list(graph.subjects(RDF.type, concept))


def get_related(graph: Graph, subject: URIRef, relation: URIRef) -> list[URIRef]:
    return list(graph.objects(subject, relation))
