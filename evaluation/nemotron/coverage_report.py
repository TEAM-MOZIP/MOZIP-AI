"""Nemotron 서울 subset을 이용한 User Mapper 매핑 커버리지 평가.

검증 대상은 "Nemotron 서울 페르소나가 MOZIP 사용자 온톨로지 vocabulary로
안정적으로 변환·매핑되는가"이며, 추천 품질·semanticScore·Policy는 다루지
않는다. gender/age_group/region 3축만 평가하고 employment_status/
household_type/income_type은 항상 NOT_EVALUATED다.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from rdflib import Graph

from app.ontology.age_group import age_group_name
from app.ontology.loader import _load_graph
from app.ontology.mapper import map_user
from app.schemas.mapping import ConceptMapping, MappingAxis, UnmappedReason, UserMappingInput
from evaluation.nemotron.sampling import (
    DATASET_REVISION,
    SAMPLES_PER_DISTRICT,
    SampledPersona,
    load_seoul_subset,
    sample_seoul_personas,
)
from evaluation.nemotron.transform import (
    build_seoul_label_to_code_index,
    district_to_region_code,
    sex_to_gender,
)

SEED = 42
ONTOLOGY_PATH = "app/ontology/mozip.owl"
OUTPUT_DIR = Path(__file__).parent / "output"

# birth_date를 생성하지 않으므로 map_user 내부에서 이 값은 age_group 계산에
# 쓰이지 않는다(AGE_GROUP은 항상 MISSING_VALUE로 기록되고 무시된다). 함수
# 시그니처를 만족시키기 위한 고정값일 뿐이다.
_UNUSED_REFERENCE_DATE = date(2026, 1, 1)

_NOT_EVALUATED_AXES = ["employment_status", "household_type", "income_type"]


class EvaluationStatus(StrEnum):
    MAPPED = "MAPPED"
    UNKNOWN_VALUE = "UNKNOWN_VALUE"
    TRANSFORM_FAILED = "TRANSFORM_FAILED"
    NOT_EVALUATED = "NOT_EVALUATED"


class RowResult(NamedTuple):
    district: str
    sex: str
    age: int
    gender_status: EvaluationStatus
    region_status: EvaluationStatus
    age_group_band: str


def _mapper_axis_status(mapping: ConceptMapping, axis: MappingAxis) -> EvaluationStatus:
    for concept in mapping.concepts:
        if concept.field == axis:
            return EvaluationStatus.MAPPED
    for unmapped in mapping.unmapped:
        if unmapped.field == axis and unmapped.reason == UnmappedReason.UNKNOWN_VALUE:
            return EvaluationStatus.UNKNOWN_VALUE
    raise AssertionError(
        f"{axis} 축에서 evaluation이 다루지 않는 결과가 나왔습니다: {mapping}"
    )


def evaluate_persona(
    persona: SampledPersona, graph: Graph, label_to_code: dict[str, str]
) -> RowResult:
    # sex 값이 계약 밖이면 여기서 즉시 예외가 전파되어 전체 실행이 중단된다.
    gender = sex_to_gender(persona.sex)
    region_code = district_to_region_code(persona.district, label_to_code)

    input_data = UserMappingInput(gender=gender, region_code=region_code)
    mapping = map_user(input_data, graph, _UNUSED_REFERENCE_DATE)

    gender_status = _mapper_axis_status(mapping, MappingAxis.GENDER)

    if region_code is None:
        # transform 자체가 실패했으므로 Mapper의 region 판정(MISSING_VALUE)을
        # 참고하지 않는다 — Mapper는 애초에 유효한 코드를 받아본 적이 없다.
        region_status = EvaluationStatus.TRANSFORM_FAILED
    else:
        region_status = _mapper_axis_status(mapping, MappingAxis.REGION)

    return RowResult(
        district=persona.district,
        sex=persona.sex,
        age=persona.age,
        gender_status=gender_status,
        region_status=region_status,
        age_group_band=age_group_name(persona.age),
    )


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def build_report(results: list[RowResult]) -> dict:
    total = len(results)
    district_counts = Counter(r.district for r in results)
    sex_counts = Counter(r.sex for r in results)
    age_band_counts = Counter(r.age_group_band for r in results)
    gender_status_counts = Counter(r.gender_status for r in results)
    region_status_counts = Counter(r.region_status for r in results)

    return {
        "metadata": {
            "dataset": "nvidia/Nemotron-Personas-Korea",
            "dataset_revision": DATASET_REVISION,
            "seed": SEED,
            "sample_size": total,
            "district_count": len(district_counts),
        },
        "sampling": {
            "total": total,
            "district_count": len(district_counts),
            "all_districts_have_expected_count": all(
                n == SAMPLES_PER_DISTRICT for n in district_counts.values()
            ),
            "district_sample_counts": dict(sorted(district_counts.items())),
            "sex_sample_counts": dict(sorted(sex_counts.items())),
            "age_group_sample_counts": dict(sorted(age_band_counts.items())),
        },
        "gender": {
            "mapped": gender_status_counts.get(EvaluationStatus.MAPPED, 0),
            "unknown_value": gender_status_counts.get(EvaluationStatus.UNKNOWN_VALUE, 0),
            "transform_failed": gender_status_counts.get(EvaluationStatus.TRANSFORM_FAILED, 0),
            "mapped_rate": _rate(gender_status_counts.get(EvaluationStatus.MAPPED, 0), total),
        },
        "region": {
            "mapped": region_status_counts.get(EvaluationStatus.MAPPED, 0),
            "unknown_value": region_status_counts.get(EvaluationStatus.UNKNOWN_VALUE, 0),
            "transform_failed": region_status_counts.get(EvaluationStatus.TRANSFORM_FAILED, 0),
            "mapped_rate": _rate(region_status_counts.get(EvaluationStatus.MAPPED, 0), total),
            "all_25_districts_represented": len(district_counts) == 25,
        },
        "age_group": {
            # age_group_name()은 정수 나이 전체 구간을 커버하므로 이 축은
            # 구조적으로 항상 MAPPED다 — 발견이 아니라 당연한 결과다.
            "mapped": total,
            "mapped_rate": 1.0 if total else 0.0,
            "band_sample_counts": dict(sorted(age_band_counts.items())),
            "note": (
                "UNDER_19 표본이 0건인 것은 Nemotron이 성인(19세 이상)만 포함하기 "
                "때문이며 데이터셋 자체의 한계다."
            ),
        },
        "not_evaluated": _NOT_EVALUATED_AXES,
        "limitations": [
            "Nemotron은 synthetic persona dataset이며 실제 서울 인구 대표성 검증이 아니다.",
            (
                "region 축은 mozip.owl 자체의 독립적인 completeness 평가가 아니라, "
                "Nemotron district 문자열 -> MOZIP Region vocabulary 변환(adapter) "
                "정합성 평가다. label->code 조회 대상이 동일한 mozip.owl에서 "
                "파생되므로 순환적 특성이 있다."
            ),
        ],
    }


def _render_markdown(report: dict) -> str:
    metadata = report["metadata"]
    sampling = report["sampling"]
    gender = report["gender"]
    region = report["region"]
    age_group = report["age_group"]

    lines = [
        "# Nemotron 기반 User Mapper 매핑 커버리지 리포트",
        "",
        "## Metadata",
        f"- dataset: {metadata['dataset']}",
        f"- dataset_revision: {metadata['dataset_revision']}",
        f"- seed: {metadata['seed']}",
        f"- sample_size: {metadata['sample_size']}",
        f"- district_count: {metadata['district_count']}",
        "",
        "## Sampling",
        f"- total: {sampling['total']}",
        f"- district_count: {sampling['district_count']}",
        f"- all_districts_have_expected_count: {sampling['all_districts_have_expected_count']}",
        f"- sex_sample_counts: {sampling['sex_sample_counts']}",
        f"- age_group_sample_counts: {sampling['age_group_sample_counts']}",
        "",
        "## Gender",
        f"- mapped: {gender['mapped']}",
        f"- unknown_value: {gender['unknown_value']}",
        f"- transform_failed: {gender['transform_failed']}",
        f"- mapped_rate: {gender['mapped_rate']}",
        "",
        "## Region",
        f"- mapped: {region['mapped']}",
        f"- unknown_value: {region['unknown_value']}",
        f"- transform_failed: {region['transform_failed']}",
        f"- mapped_rate: {region['mapped_rate']}",
        f"- all_25_districts_represented: {region['all_25_districts_represented']}",
        "",
        "## AgeGroup",
        f"- mapped: {age_group['mapped']}",
        f"- mapped_rate: {age_group['mapped_rate']}",
        f"- band_sample_counts: {age_group['band_sample_counts']}",
        f"- note: {age_group['note']}",
        "",
        "## NOT_EVALUATED",
    ]
    lines.extend(f"- {axis}" for axis in report["not_evaluated"])
    lines.append("")
    lines.append("## Limitations")
    lines.extend(f"{i + 1}. {item}" for i, item in enumerate(report["limitations"]))
    lines.append("")
    return "\n".join(lines)


def _write_report(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "baseline.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "baseline.md").write_text(_render_markdown(report), encoding="utf-8")


def run() -> dict:
    graph = _load_graph(ONTOLOGY_PATH)
    label_to_code = build_seoul_label_to_code_index(graph)

    seoul_table = load_seoul_subset()
    personas = sample_seoul_personas(seoul_table, seed=SEED)

    results = [evaluate_persona(persona, graph, label_to_code) for persona in personas]

    report = build_report(results)
    _write_report(report, OUTPUT_DIR)
    return report


if __name__ == "__main__":
    run()
