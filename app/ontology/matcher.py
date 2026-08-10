from rdflib import Graph, Namespace, URIRef

from app.ontology.graph import get_related
from app.schemas.mapping import ConceptMapping, MappedConcept, MappingAxis
from app.schemas.semantic_match import InferencePath, MatchedConcept, SemanticMatchResult

MZ = Namespace("http://mozip.ai/ontology#")


def _group_by_axis(concepts: list[MappedConcept]) -> dict[MappingAxis, list[MappedConcept]]:
    grouped: dict[MappingAxis, list[MappedConcept]] = {}
    for concept in concepts:
        grouped.setdefault(concept.field, []).append(concept)
    return grouped


def _match_axis(
    axis: MappingAxis,
    user_concepts: list[MappedConcept],
    policy_concepts: list[MappedConcept],
    graph: Graph,
) -> tuple[list[MatchedConcept], list[InferencePath]]:
    # (axis, user_concept_uri, policy_concept_uri) 조합이 같으면 같은 일치 쌍으로 보고
    # 한 번만 기록한다. Mapper가 각 축을 중복 없이 넘겨주더라도, Matcher가 이 불변조건에
    # 의존하지 않도록 여기서 직접 중복을 제거한다. 최초 발견 순서를 유지한다.
    seen_pairs: set[tuple[MappingAxis, str, str]] = set()
    matches: list[MatchedConcept] = []
    inference_paths: list[InferencePath] = []
    exact_matched_user_uris: set[str] = set()

    for user_concept in user_concepts:
        for policy_concept in policy_concepts:
            if user_concept.concept_uri != policy_concept.concept_uri:
                continue

            pair_key = (axis, user_concept.concept_uri, policy_concept.concept_uri)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            exact_matched_user_uris.add(user_concept.concept_uri)

            matches.append(
                MatchedConcept(
                    axis=axis,
                    user_concept_uri=user_concept.concept_uri,
                    user_concept_code=user_concept.concept_code,
                    policy_concept_uri=policy_concept.concept_uri,
                    policy_concept_code=policy_concept.concept_code,
                )
            )

    # REGION 축 한정 PART_OF 1홉 간접 매칭. 이미 exact로 매치된 user concept는 같은
    # 근거를 중복 기록하지 않도록 건너뛴다 (exact 우선). 방향은 user --PART_OF--> policy
    # 만 허용하며, get_related가 1홉만 조회하므로 반대 방향·재귀 탐색은 발생하지 않는다.
    if axis == MappingAxis.REGION:
        for user_concept in user_concepts:
            if user_concept.concept_uri in exact_matched_user_uris:
                continue

            part_of_targets = {
                str(target)
                for target in get_related(graph, URIRef(user_concept.concept_uri), MZ.partOf)
            }

            for policy_concept in policy_concepts:
                if policy_concept.concept_uri not in part_of_targets:
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
                inference_paths.append(
                    InferencePath(
                        axis=axis,
                        from_concept_uri=user_concept.concept_uri,
                        relations=["PART_OF"],
                        to_concept_uri=policy_concept.concept_uri,
                    )
                )

    return matches, inference_paths


def match_concepts(
    user_mapping: ConceptMapping, policy_mapping: ConceptMapping, graph: Graph
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
    inference_paths: list[InferencePath] = []
    matched_axis_count = 0

    for axis in evaluable_axes:
        axis_matches, axis_inference_paths = _match_axis(
            axis, user_by_axis[axis], policy_by_axis[axis], graph
        )
        if axis_matches:
            matched_axis_count += 1
            matched_concepts.extend(axis_matches)
            inference_paths.extend(axis_inference_paths)

    semantic_score = round(matched_axis_count / len(evaluable_axes), 4)

    return SemanticMatchResult(
        semantic_score=semantic_score,
        matched_concepts=matched_concepts,
        inference_paths=inference_paths,
    )
