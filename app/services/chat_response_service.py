import logging
from collections.abc import Callable

from app.clients.llm_client import LlmClient
from app.core.config import get_settings
from app.prompts.chat_response import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.chat_response import (
    ChatBlock,
    ChatBlockPolicy,
    ChatBlockType,
    ChatResponseRequest,
    ChatResponseResponse,
    ChatResponseType,
    PolicyFit,
)

logger = logging.getLogger("mozip_ai.chat")

MAX_FOLLOW_UPS = 3
MAX_QUICK_REPLIES = 6
MIN_COMPARISON_POLICIES = 2


def generate_chat_response(
    request: ChatResponseRequest, llm_client: LlmClient
) -> ChatResponseResponse:
    user_content = build_user_content(request)
    response = llm_client.generate_structured(
        SYSTEM_INSTRUCTION,
        user_content,
        ChatResponseResponse,
        timeout_seconds=get_settings().gemini_chat_timeout_seconds,
    )
    sanitized = _sanitize(response, request)
    # 화면에 블록이 기대대로 안 나올 때 원인을 가르기 위한 로그: 모델이 만든 블록과 정리 후 남은 블록.
    logger.info(
        "chat answer type=%s raw_blocks=%s notes=%s raw_policy_ids=%s blocks=%s grounding_ids=%s "
        "follow_ups=%d",
        response.response_type,
        [f"{note.policy_id}:{note.fit.value}" for note in response.policy_notes],
        [block.type.value for block in response.blocks],
        [
            [policy.policy_id for policy in block.policies] + block.policy_ids
            for block in response.blocks
            if block.type == ChatBlockType.POLICY_GROUP
        ],
        [block.type.value for block in sanitized.blocks],
        [policy.policy_id for policy in request.grounding_policies],
        len(sanitized.follow_ups),
    )
    return sanitized


def _sanitize(response: ChatResponseResponse, request: ChatResponseRequest) -> ChatResponseResponse:
    """모델 출력에서 그릴 수 없는 블록을 걸러낸다.

    - 주어진 정책(grounding·policyDetail)에 없는 policyId는 버린다(없는 정책을 지어내지 않도록).
    - 같은 정책은 답변 전체에서 한 번만 카드로 보여준다.
    - 내용이 빈 블록은 버리고, 남은 블록이 없으면 reply를 텍스트 블록으로 보여준다.
    """
    resolve = _policy_resolver(request)
    shown_policy_ids: set[int] = set()
    blocks = [
        cleaned
        for block in response.blocks
        if (cleaned := _clean_block(block, resolve, shown_policy_ids)) is not None
    ]
    if not blocks and response.reply.strip():
        blocks = [ChatBlock(type=ChatBlockType.TEXT, text=response.reply.strip())]

    group_blocks = _policy_groups(response, request, resolve, blocks)
    if group_blocks:
        blocks = _insert_policy_groups(blocks, group_blocks)

    return response.model_copy(
        update={
            "blocks": blocks,
            "policy_notes": [],
            "follow_ups": _unique_non_blank(response.follow_ups)[:MAX_FOLLOW_UPS],
        }
    )


GROUP_TITLES = {
    ChatResponseType.RECOMMEND: ("딱 맞는 정책", "함께 보면 좋은 정책"),
    ChatResponseType.COMPARE: ("비교한 정책", "비교한 정책"),
}
DEFAULT_GROUP_TITLES = ("이 정책 자세히 보기", "함께 보면 좋은 정책")
MAX_RELATED_CARDS = 2


def _policy_groups(
    response: ChatResponseResponse,
    request: ChatResponseRequest,
    resolve: Callable[[int, str | None], int | None],
    cleaned_blocks: list[ChatBlock],
) -> list[ChatBlock]:
    """policyNotes로 정책 카드 그룹을 만든다(블록 안의 POLICY_GROUP보다 우선).

    - BEST는 '딱 맞는 정책', RELATED는 '함께 보면 좋은 정책'(최대 2개), EXCLUDE는 보여주지 않는다.
    - 모델이 notes를 비웠으면 블록의 POLICY_GROUP을 그대로 쓰고, 그것도 없는데 추천·비교 답변이면 주어진 정책을
      순서대로 카드로 보여준다(정책이 화면에서 사라지지 않게).
    """
    shown_policy_ids: set[int] = set()
    best: list[ChatBlockPolicy] = []
    related: list[ChatBlockPolicy] = []
    for note in response.policy_notes:
        resolved = resolve(note.policy_id, note.title)
        if resolved is None or resolved in shown_policy_ids or note.fit == PolicyFit.EXCLUDE:
            continue
        shown_policy_ids.add(resolved)
        card = ChatBlockPolicy(
            policy_id=resolved,
            title=note.title or None,
            reason=note.reason.strip(),
            highlight=(note.highlight or "").strip() or None,
        )
        (best if note.fit == PolicyFit.BEST else related).append(card)
    related = related[:MAX_RELATED_CARDS]

    if not best and not related:
        # 모델이 모든 정책을 EXCLUDE로 판단했거나 블록 안 카드가 살아 있으면 그대로 둔다.
        if response.policy_notes or any(
            block.type == ChatBlockType.POLICY_GROUP for block in cleaned_blocks
        ):
            return []
        if request.grounding_policies and response.response_type in GROUP_TITLES:
            best = [
                ChatBlockPolicy(policy_id=policy.policy_id, reason="")
                for policy in request.grounding_policies
            ]

    best_title, related_title = GROUP_TITLES.get(response.response_type, DEFAULT_GROUP_TITLES)
    groups = []
    if best:
        groups.append(ChatBlock(type=ChatBlockType.POLICY_GROUP, title=best_title, policies=best))
    if related:
        groups.append(
            ChatBlock(type=ChatBlockType.POLICY_GROUP, title=related_title, policies=related)
        )
    return groups


def _insert_policy_groups(blocks: list[ChatBlock], groups: list[ChatBlock]) -> list[ChatBlock]:
    """카드 그룹을 블록 사이에 넣는다: 모델이 POLICY_GROUP을 둔 자리(없으면 빠른 선택 칩 앞, 그것도 없으면 맨 끝)."""
    others = [block for block in blocks if block.type != ChatBlockType.POLICY_GROUP]
    position = next(
        (index for index, block in enumerate(blocks) if block.type == ChatBlockType.POLICY_GROUP),
        None,
    )
    if position is not None:
        position = sum(1 for block in blocks[:position] if block.type != ChatBlockType.POLICY_GROUP)
    else:
        position = next(
            (i for i, block in enumerate(others) if block.type == ChatBlockType.QUICK_REPLIES),
            len(others),
        )
    return others[:position] + groups + others[position:]


def _policy_resolver(request: ChatResponseRequest) -> Callable[[int, str | None], int | None]:
    """모델이 쓴 정책 참조를 실제 policyId로 바꾼다.

    1) 주어진 policyId 그대로면 그대로, 2) 제목이 주어진 정책 제목과 같으면 그 정책, 3) 목록 순번(1부터)을 id로
    쓴 경우 그 순번의 정책. 어디에도 맞지 않으면 None(지어낸 정책으로 보고 버린다).
    """
    ordered = [policy.policy_id for policy in request.grounding_policies]
    id_by_title = {policy.title.strip(): policy.policy_id for policy in request.grounding_policies}
    detail = request.policy_detail
    if detail is not None and detail.policy_id is not None:
        id_by_title.setdefault(detail.title.strip(), detail.policy_id)
    known_ids = set(id_by_title.values()) | set(ordered)

    def resolve(policy_id: int, title: str | None) -> int | None:
        if policy_id in known_ids:
            return policy_id
        if title and title.strip() in id_by_title:
            return id_by_title[title.strip()]
        if 1 <= policy_id <= len(ordered):
            return ordered[policy_id - 1]
        return None

    return resolve


def _clean_block(
    block: ChatBlock,
    resolve: Callable[[int, str | None], int | None],
    shown_policy_ids: set[int],
) -> ChatBlock | None:
    text = (block.text or "").strip() or None

    if block.type in (ChatBlockType.TEXT, ChatBlockType.CONCLUSION):
        return block.model_copy(update={"text": text}) if text else None

    if block.type == ChatBlockType.POLICY_GROUP:
        # 모델이 policies 대신 policyIds에만 id를 넣는 경우가 있어, 그때는 id만으로 카드를 만든다(추천 이유 없음).
        candidates = block.policies or [
            ChatBlockPolicy(policy_id=policy_id, reason="") for policy_id in block.policy_ids
        ]
        policies = []
        for policy in candidates:
            resolved = resolve(policy.policy_id, policy.title)
            if resolved is not None and resolved not in shown_policy_ids:
                shown_policy_ids.add(resolved)
                policies.append(policy.model_copy(update={"policy_id": resolved}))
        return block.model_copy(update={"policies": policies}) if policies else None

    if block.type == ChatBlockType.COMPARISON:
        resolved_ids = [resolve(policy_id, None) for policy_id in block.policy_ids]
        keep = [index for index, policy_id in enumerate(resolved_ids) if policy_id is not None]
        if len(keep) < MIN_COMPARISON_POLICIES:
            return None
        rows = [
            row.model_copy(update={"values": [row.values[index] for index in keep]})
            for row in block.rows
            if row.label.strip() and len(row.values) == len(block.policy_ids)
        ]
        if not rows:
            return None
        return block.model_copy(
            update={"policy_ids": [resolved_ids[index] for index in keep], "rows": rows}
        )

    if block.type == ChatBlockType.STEPS:
        steps = [step for step in block.steps if step.title.strip()]
        return block.model_copy(update={"steps": steps}) if steps else None

    if block.type == ChatBlockType.CHECKLIST:
        items = _unique_non_blank(block.items)
        return block.model_copy(update={"items": items}) if items else None

    if block.type == ChatBlockType.TERM:
        title = (block.title or "").strip()
        return block.model_copy(update={"title": title, "text": text}) if title and text else None

    if block.type == ChatBlockType.QUICK_REPLIES:
        items = _unique_non_blank(block.items)[:MAX_QUICK_REPLIES]
        return block.model_copy(update={"text": text, "items": items}) if items else None

    return None


def _unique_non_blank(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in result:
            result.append(stripped)
    return result
