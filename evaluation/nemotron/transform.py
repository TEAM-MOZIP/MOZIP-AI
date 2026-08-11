"""Nemotron persona 원본 값(sex/district) → MOZIP 온톨로지 vocabulary 변환.

이 모듈은 판정 로직 없이 순수 변환만 담당한다. district 변환 실패는 Mapper의
MISSING_VALUE/UNKNOWN_VALUE와 의미가 다른 "TRANSFORM_FAILED"이므로, 이 모듈은
성공 시 Region code(str)를, 실패 시 None을 반환할 뿐 Mapper를 직접 호출하지
않는다. age → AgeGroup 변환은 운영 Mapper와 공유하는 app.ontology.age_group을
그대로 사용하므로 이 모듈에서 다루지 않는다.
"""

from __future__ import annotations

import unicodedata

from rdflib import RDFS, Graph, URIRef

from app.ontology.graph import get_individuals, get_related
from app.schemas.mapping import Gender

_MZ_NAMESPACE = "http://mozip.ai/ontology#"
_MZ_REGION = URIRef(f"{_MZ_NAMESPACE}Region")
_MZ_SEOUL = URIRef(f"{_MZ_NAMESPACE}SEOUL")
_MZ_PART_OF = URIRef(f"{_MZ_NAMESPACE}partOf")

_DISTRICT_PREFIX = "서울-"
_EXPECTED_SEOUL_DISTRICT_COUNT = 25

_SEX_TO_GENDER: dict[str, Gender] = {
    "남자": Gender.MALE,
    "여자": Gender.FEMALE,
}


class UnexpectedSexValueError(Exception):
    """Nemotron sex 값이 계약("남자"/"여자") 밖일 때 발생한다. source dataset
    contract가 깨졌다는 신호이므로 조용히 건너뛰지 않고 즉시 중단시킨다."""


class UnexpectedDistrictFormatError(Exception):
    """district 값이 예상한 '서울-XX구' 형식이 아닐 때 발생한다."""


class RegionLabelIndexError(Exception):
    """mozip.owl에서 만든 서울 자치구 label→code 인덱스가 기대한 계약(자치구
    25개, 각 자치구 고유 label 1개)을 어길 때 발생한다. evaluation adapter가
    쓰는 데이터 계약 오류이며, mozip.owl 자체의 무결성을 보장하지는 않는다."""


def sex_to_gender(sex: str) -> Gender:
    normalized = unicodedata.normalize("NFC", sex)
    if normalized not in _SEX_TO_GENDER:
        raise UnexpectedSexValueError(
            f"예상 밖 sex 값입니다: {sex!r}. 허용값은 '남자'/'여자'뿐입니다."
        )
    return _SEX_TO_GENDER[normalized]


def build_seoul_label_to_code_index(graph: Graph) -> dict[str, str]:
    """mozip.owl에서 SEOUL의 하위(partOf) 자치구 label→code 인덱스를 만든다.

    별도의 25개 하드코딩 테이블을 두지 않고, Git tracked인 mozip.owl을 유일한
    Source of Truth로 사용한다. code는 각 Region 개체의 URI local name이다.

    현재 mozip.owl 계약(자치구 25개, 각 자치구 고유 label 1개, label→code
    1:1)을 벗어나면 조용히 넘어가지 않고 RegionLabelIndexError를 즉시 던진다
    — label 없는 자치구나 중복 label은 발견 시점에 바로 실패하고, 최종
    자치구 수가 25개가 아니면 인덱스 구성이 끝난 뒤 실패한다.
    """
    index: dict[str, str] = {}
    for region in get_individuals(graph, _MZ_REGION):
        if _MZ_SEOUL not in get_related(graph, region, _MZ_PART_OF):
            continue

        label = graph.value(region, RDFS.label)
        if label is None:
            raise RegionLabelIndexError(f"자치구 Region에 rdfs:label이 없습니다: {region}")

        code = str(region).removeprefix(_MZ_NAMESPACE)
        normalized_label = unicodedata.normalize("NFC", str(label))

        if normalized_label in index:
            raise RegionLabelIndexError(
                f"'{normalized_label}' label이 둘 이상의 자치구 Region에 중복됩니다: "
                f"기존={index[normalized_label]!r}, 신규={code!r}"
            )

        index[normalized_label] = code

    if len(index) != _EXPECTED_SEOUL_DISTRICT_COUNT:
        raise RegionLabelIndexError(
            f"서울 자치구 label 인덱스가 {len(index)}개입니다. "
            f"{_EXPECTED_SEOUL_DISTRICT_COUNT}개가 아니므로 mozip.owl 계약이 바뀌었을 수 있습니다."
        )

    return index


def district_to_region_code(district: str, label_to_code: dict[str, str]) -> str | None:
    """'서울-마포구' 같은 원본 문자열을 'SEOUL_MAPO' 같은 Region code로 변환한다.

    '서울-' 접두어가 없는 등 예상과 다른 형식이면 추측하지 않고 즉시 예외를
    던진다. 접두어를 뗀 뒤 label 인덱스에 없는 값(예: 존재하지 않는 자치구)은
    예외가 아니라 None을 반환한다 — 이 경우는 개별 row의 변환 실패이지 데이터
    계약 자체가 깨진 것은 아니기 때문이다. 호출자는 None을 TRANSFORM_FAILED로
    집계해야 하며, 원본 문자열이나 None을 그대로 region_code로 Mapper에
    전달해서는 안 된다.
    """
    normalized = unicodedata.normalize("NFC", district)
    if not normalized.startswith(_DISTRICT_PREFIX):
        raise UnexpectedDistrictFormatError(
            f"예상한 '{_DISTRICT_PREFIX}' 접두어 형식이 아닙니다: {district!r}"
        )

    label = normalized.removeprefix(_DISTRICT_PREFIX)
    return label_to_code.get(label)
