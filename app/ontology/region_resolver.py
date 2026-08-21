from rdflib import RDFS, Graph, Namespace

from app.ontology.graph import get_individuals

MZ = Namespace("http://mozip.ai/ontology#")

_SEOUL_CODE = "SEOUL"
_SEOUL_ALIASES = ("서울", "서울시")


def _build_label_to_code(graph: Graph) -> dict[str, str]:
    label_to_code: dict[str, str] = {}
    for uri in get_individuals(graph, MZ.Region):
        label = graph.value(uri, RDFS.label)
        if label is None:
            continue
        code = str(uri).removeprefix(str(MZ))
        label_to_code[str(label)] = code
    return label_to_code


def resolve_region(expression: str, graph: Graph) -> str | None:
    text = expression.strip()
    label_to_code = _build_label_to_code(graph)

    if text in label_to_code:
        return label_to_code[text]

    if text in _SEOUL_ALIASES:
        return _SEOUL_CODE if _SEOUL_CODE in label_to_code.values() else None

    if len(text) >= 2:
        candidate = f"{text}구"
        if candidate in label_to_code:
            return label_to_code[candidate]

    return None
