"""Nemotron-Personas-Korea 서울 subset 로딩 및 자치구별 결정적 샘플링.

MOZIP-AI 런타임(app/)과 완전히 분리된 evaluation 전용 모듈이다. HuggingFace
Hub에서 필요한 4개 컬럼(sex/age/province/district)만 parquet에서 읽어오며,
1M rows 전체나 다른 컬럼(페르소나 서술 텍스트 등)은 적재하지 않는다.
"""

from __future__ import annotations

import random
from typing import NamedTuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

DATASET_REPO_ID = "nvidia/Nemotron-Personas-Korea"
# main의 floating 참조 대신 고정 commit hash를 사용해 재현성을 보장한다.
# https://huggingface.co/api/datasets/nvidia/Nemotron-Personas-Korea 의 "sha" 필드로 확인.
DATASET_REVISION = "ada0f5b53a38bb5a30cce09358adde883c1ab63a"
_PARQUET_FILE_COUNT = 9
_REQUIRED_COLUMNS = ["sex", "age", "province", "district"]
_TARGET_PROVINCE = "서울"
_EXPECTED_DISTRICT_COUNT = 25

SAMPLES_PER_DISTRICT = 20


class SampledPersona(NamedTuple):
    sex: str
    age: int
    district: str


class DistrictSampleShortageError(Exception):
    """특정 자치구의 실제 가용 row 수가 요구 표본 수보다 적을 때 발생한다."""


class UnexpectedDistrictCountError(Exception):
    """서울 subset의 고유 district 값 개수가 25개가 아닐 때 발생한다."""


def load_seoul_subset() -> pa.Table:
    """9개 parquet 파일에서 4개 컬럼만 읽어 province == '서울' row만 반환한다."""
    tables = []
    for index in range(_PARQUET_FILE_COUNT):
        filename = f"data/train-{index:05d}-of-00009.parquet"
        path = hf_hub_download(
            repo_id=DATASET_REPO_ID,
            repo_type="dataset",
            revision=DATASET_REVISION,
            filename=filename,
        )
        table = pq.read_table(path, columns=_REQUIRED_COLUMNS)
        tables.append(table.filter(pc.equal(table["province"], _TARGET_PROVINCE)))
    return pa.concat_tables(tables)


def sample_seoul_personas(
    seoul_table: pa.Table,
    seed: int,
    samples_per_district: int = SAMPLES_PER_DISTRICT,
) -> list[SampledPersona]:
    """자치구별로 중복 없이 정확히 samples_per_district건을 고정 seed로 뽑는다.

    district 오름차순으로 처리하고, 각 district 내부에서는 뽑힌 row 인덱스를
    오름차순 정렬해 반환하므로 결과 순서는 seed와 무관하게 항상 결정적이다.
    """
    districts = sorted(set(seoul_table.column("district").to_pylist()))
    if len(districts) != _EXPECTED_DISTRICT_COUNT:
        raise UnexpectedDistrictCountError(
            f"서울 subset의 district가 {len(districts)}개입니다. "
            f"{_EXPECTED_DISTRICT_COUNT}개가 아니므로 데이터 계약이 바뀌었을 수 있습니다."
        )

    rng = random.Random(seed)
    sampled: list[SampledPersona] = []

    for district in districts:
        district_table = seoul_table.filter(pc.equal(seoul_table["district"], district))
        available = district_table.num_rows
        if available < samples_per_district:
            raise DistrictSampleShortageError(
                f"'{district}' 자치구의 가용 row가 {available}건으로 "
                f"요구 표본 수({samples_per_district}건)보다 적습니다."
            )

        # replacement 없이 뽑고, 최종 순서는 인덱스 오름차순으로 고정한다.
        chosen_indices = sorted(rng.sample(range(available), samples_per_district))
        sex_values = district_table.column("sex").to_pylist()
        age_values = district_table.column("age").to_pylist()
        for i in chosen_indices:
            sampled.append(
                SampledPersona(sex=sex_values[i], age=age_values[i], district=district)
            )

    return sampled
