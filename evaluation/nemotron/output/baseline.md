# Nemotron 기반 User Mapper 매핑 커버리지 리포트

## Metadata
- dataset: nvidia/Nemotron-Personas-Korea
- dataset_revision: ada0f5b53a38bb5a30cce09358adde883c1ab63a
- seed: 42
- sample_size: 500
- district_count: 25

## Sampling
- total: 500
- district_count: 25
- all_districts_have_expected_count: True
- sex_sample_counts: {'남자': 231, '여자': 269}
- age_group_sample_counts: {'AGE_19_24': 32, 'AGE_25_29': 44, 'AGE_30_34': 56, 'AGE_35_49': 126, 'AGE_50_64': 131, 'AGE_65_PLUS': 111}

## Gender
- mapped: 500
- unknown_value: 0
- transform_failed: 0
- mapped_rate: 1.0

## Region
- mapped: 500
- unknown_value: 0
- transform_failed: 0
- mapped_rate: 1.0
- all_25_districts_represented: True

## AgeGroup
- mapped: 500
- mapped_rate: 1.0
- band_sample_counts: {'AGE_19_24': 32, 'AGE_25_29': 44, 'AGE_30_34': 56, 'AGE_35_49': 126, 'AGE_50_64': 131, 'AGE_65_PLUS': 111}
- note: UNDER_19 표본이 0건인 것은 Nemotron이 성인(19세 이상)만 포함하기 때문이며 데이터셋 자체의 한계다.

## NOT_EVALUATED
- employment_status
- household_type
- income_type

## Limitations
1. Nemotron은 synthetic persona dataset이며 실제 서울 인구 대표성 검증이 아니다.
2. region 축은 mozip.owl 자체의 독립적인 completeness 평가가 아니라, Nemotron district 문자열 -> MOZIP Region vocabulary 변환(adapter) 정합성 평가다. label->code 조회 대상이 동일한 mozip.owl에서 파생되므로 순환적 특성이 있다.
