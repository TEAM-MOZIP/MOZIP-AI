from functools import lru_cache

from rdflib import Graph

from app.core.config import get_settings
from app.core.exceptions import AppException


def _load_graph(path: str) -> Graph:
    graph = Graph()
    try:
        graph.parse(path, format="turtle")
    except FileNotFoundError as exc:
        raise AppException(
            f"온톨로지 파일을 찾을 수 없습니다: {path}",
            code="ONTOLOGY_FILE_NOT_FOUND",
            status_code=500,
        ) from exc
    except Exception as exc:
        raise AppException(
            "온톨로지 파일을 불러오는 중 오류가 발생했습니다.",
            code="ONTOLOGY_LOAD_FAILED",
            status_code=500,
        ) from exc
    return graph


@lru_cache
def get_ontology_graph() -> Graph:
    return _load_graph(get_settings().ontology_file_path)
