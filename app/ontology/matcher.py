from app.schemas.mapping import ConceptMapping, MappedConcept, MappingAxis
from app.schemas.semantic_match import MatchedConcept, SemanticMatchResult


def _group_by_axis(concepts: list[MappedConcept]) -> dict[MappingAxis, list[MappedConcept]]:
    grouped: dict[MappingAxis, list[MappedConcept]] = {}
    for concept in concepts:
        grouped.setdefault(concept.field, []).append(concept)
    return grouped


def _match_axis(
    axis: MappingAxis,
    user_concepts: list[MappedConcept],
    policy_concepts: list[MappedConcept],
) -> list[MatchedConcept]:
    # (axis, user_concept_uri, policy_concept_uri) 조합이 같으면 같은 일치 쌍으로 보고
    # 한 번만 기록한다. Mapper가 각 축을 중복 없이 넘겨주더라도, Matcher가 이 불변조건에
    # 의존하지 않도록 여기서 직접 중복을 제거한다. 최초 발견 순서를 유지한다.
    seen_pairs: set[tuple[MappingAxis, str, str]] = set()
    matches: list[MatchedConcept] = []
    for user_concept in user_concepts:
        for policy_concept in policy_concepts:
            if user_concept.concept_uri != policy_concept.concept_uri:
                continue

            pair_key = (axis, user_concept.concept_uri, policy_concept.concept_uri)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            matches.append(
                MatchedConcept(
                    axis=axis,
                    user_concept_uri=user_concept.concept_uri,
                    user_concept_code=user_concept.concept_code,
                    policy_concept_uri=policy_concept.concept_uri,
                    policy_concept_code=policy_concept.concept_code,
                )
            )
    return matches


def match_concepts(
    user_mapping: ConceptMapping, policy_mapping: ConceptMapping
) -> SemanticMatchResult:
    user_by_axis = _group_by_axis(user_mapping.concepts)
    policy_by_axis = _group_by_axis(policy_mapping.concepts)

    # 평가 가능 축: 양쪽에 매핑된 개념(concepts)이 하나 이상 있는 공통 축.
    # UNKNOWN_VALUE/MISSING_VALUE는 concepts가 아니라 unmapped에만 기록되므로,
    # 한 축에 UNKNOWN_VALUE가 섞여 있어도 정상 매핑된 개념이 하나라도 있으면
    # 자동으로 평가 대상에 포함된다.
    evaluable_axes = [
        axis for axis in MappingAxis if user_by_axis.get(axis) and policy_by_axis.get(axis)
    ]

    if not evaluable_axes:
        return SemanticMatchResult(semantic_score=None)

    matched_concepts: list[MatchedConcept] = []
    matched_axis_count = 0

    for axis in evaluable_axes:
        axis_matches = _match_axis(axis, user_by_axis[axis], policy_by_axis[axis])
        if axis_matches:
            matched_axis_count += 1
            matched_concepts.extend(axis_matches)

    semantic_score = round(matched_axis_count / len(evaluable_axes), 4)

    return SemanticMatchResult(semantic_score=semantic_score, matched_concepts=matched_concepts)
