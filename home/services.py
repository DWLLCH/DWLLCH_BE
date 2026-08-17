import json

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors, types
from pydantic import BaseModel, Field, ValidationError

from chat.models import RiskCheckMessage

from .models import Policy


class ChatbotAnswerResult(BaseModel):
    answer: str
    answerable: bool


CHATBOT_PROMPT = """
당신은 자립준비청년을 위한 제도 안내 챗봇입니다.

다음 정책을 반드시 지키세요.

1. 아래 "정책 정보" 안에 있는 내용만 사용해서 답하세요.
2. 정책 정보에 없는 금액, 조건, 날짜를 추측해서 답하지 마세요.
3. 정책 정보로 답할 수 없는 질문이면, answerable을 false로 하고
   "정확한 확인이 어렵습니다. 관련 기관에 직접 문의해보세요" 같은 취지로 답하세요.
4. 답변은 친절하고 간결한 한국어로 작성하세요.
"""


def get_policy_chatbot_answer(question: str, policy_id: int | None = None) -> ChatbotAnswerResult:
    client = _get_client()

    if policy_id:
        try:
            policy = Policy.objects.get(id=policy_id)
            policy_context = (
                f"제목: {policy.title}\n"
                f"소개: {policy.content}\n"
                f"신청자격: {policy.eligibility}\n"
                f"신청방법: {policy.application_method}\n"
                f"준비서류: {policy.required_documents}"
            )
        except Policy.DoesNotExist:
            policy_context = "해당 정책 정보를 찾을 수 없습니다."
    else:
        related_policies = Policy.objects.filter(title__icontains=question)[:5]
        if related_policies:
            policy_context = "\n\n".join(
                f"[{p.title}]\n소개: {p.content}\n신청자격: {p.eligibility}"
                for p in related_policies
            )
        else:
            policy_context = "관련 정책 정보를 찾지 못했습니다."

    prompt = f"""
{CHATBOT_PROMPT}

정책 정보:
{policy_context}

사용자 질문:
{question}
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ChatbotAnswerResult,
            ),
        )
    except (genai_errors.APIError, httpx.HTTPError, TimeoutError) as exc:
        raise GeminiRequestError from exc

    try:
        return _parse_response(response, ChatbotAnswerResult)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiRequestError from exc

class MatchedPolicy(BaseModel):
    policy_id: int
    match_reason: str


class ConditionMatchResult(BaseModel):
    matches: list[MatchedPolicy] = Field(default_factory=list)


class GeminiRequestError(Exception):
    """Gemini API 또는 네트워크 호출 실패."""


CONDITION_MATCH_PROMPT = """
당신은 자립준비청년에게 맞는 지원 정책을 추천하는 한국어 지원 챗봇입니다.

다음 정책을 반드시 지키세요.

1. 아래 "정책 목록"에 있는 정책 중에서만 골라서 추천하세요.
2. 정책 id는 반드시 정책 목록에 있는 id 그대로 사용하세요.
3. 정책 내용(제목, 자격 요건, 금액 등)을 새로 만들거나 바꾸지 마세요.
4. 사용자 상황에 왜 이 정책이 맞는지 이유를 한 문장(40자 이내)으로 작성하세요.
5. 명확하게 맞는 정책이 없으면 matches를 빈 배열로 반환하세요.
6. 최대 5개까지만 추천하세요.
7. "최근 챗봇 상담에서 자주 물어본 주제"가 있다면, 관련 정책의 추천 우선순위를 높이고 이유에 자연스럽게 반영하세요.
"""

CHAT_TOPIC_KEYWORDS = {
    "HOUSING": ["주거", "월세", "전세", "집", "임대"],
    "FINANCE": ["자립수당", "정착금", "대출", "적금"],
    "EMPLOYMENT": ["취업", "일자리", "알바", "직장"],
}


def _get_client():
    if not settings.GEMINI_HOME_API_KEY:
        raise GeminiRequestError("GEMINI_HOME_API_KEY가 설정되지 않았습니다.")

    return genai.Client(
        api_key=settings.GEMINI_HOME_API_KEY,
        http_options=types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS),
    )


def _parse_response(response, schema):
    if getattr(response, "parsed", None):
        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        return schema.model_validate(parsed)

    return schema.model_validate(json.loads(response.text))


def get_frequent_chat_topics(user, limit=1):
    messages = RiskCheckMessage.objects.filter(
        session__user=user, sender=RiskCheckMessage.Sender.USER
    ).values_list("content", flat=True)

    counts = {topic: 0 for topic in CHAT_TOPIC_KEYWORDS}
    for content in messages:
        for topic, keywords in CHAT_TOPIC_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                counts[topic] += 1

    sorted_topics = sorted(counts.items(), key=lambda x: -x[1])
    return [topic for topic, count in sorted_topics[:limit] if count > 0]


def match_policies_by_condition(policies, user):
    if not policies:
        return ConditionMatchResult(matches=[])

    client = _get_client()

    policy_lines = "\n".join(
        f"- id={p.id}, 제목={p.title}, 카테고리={p.category}, 자격요건={p.eligibility}"
        for p in policies
    )

    chat_topics = get_frequent_chat_topics(user)
    chat_topics_text = ", ".join(chat_topics) if chat_topics else "없음"

    profile_text = (
        f"생활 형태: {', '.join(user.living_status) or '정보 없음'}\n"
        f"필요한 도움: {', '.join(user.needed_help) or '정보 없음'}\n"
        f"주거 상황: {user.housing_situation or '정보 없음'}\n"
        f"최근 챗봇 상담에서 자주 물어본 주제: {chat_topics_text}"
    )

    prompt = f"""
{CONDITION_MATCH_PROMPT}

정책 목록:
{policy_lines}

사용자 상황:
{profile_text}
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ConditionMatchResult,
            ),
        )
    except (genai_errors.APIError, httpx.HTTPError, TimeoutError) as exc:
        raise GeminiRequestError from exc

    try:
        return _parse_response(response, ConditionMatchResult)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiRequestError from exc