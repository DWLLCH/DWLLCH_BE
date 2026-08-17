from .models import Policy
import json

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors, types
from pydantic import BaseModel, Field, ValidationError

def get_policy_chatbot_answer(question: str, policy_id: int | None = None) -> str:
    """
    제도 전용 챗봇 질의에 대한 답변을 생성한다.
    TODO: 실제 AI API 연동으로 교체 예정 (지금은 임시 응답)
    """
    context = ""
    if policy_id:
        try:
            policy = Policy.objects.get(id=policy_id)
            context = f"[{policy.title}] {policy.content}"
        except Policy.DoesNotExist:
            context = ""

    # TODO: 여기서 외부 AI API(requests/httpx) 호출로 교체
    if context:
        return f"'{question}'에 대한 답변입니다. 관련 정책: {context[:100]}..."
    return f"'{question}'에 대한 일반적인 답변 준비 중입니다."


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
"""


def _get_client():
    if not settings.GEMINI_API_KEY:
        raise GeminiRequestError("GEMINI_API_KEY가 설정되지 않았습니다.")

    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=settings.GEMINI_TIMEOUT_MS),
    )


def _parse_response(response, schema):
    if getattr(response, "parsed", None):
        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        return schema.model_validate(parsed)

    return schema.model_validate(json.loads(response.text))


def match_policies_by_condition(policies, user):
    if not policies:
        return ConditionMatchResult(matches=[])

    client = _get_client()

    policy_lines = "\n".join(
        f"- id={p.id}, 제목={p.title}, 카테고리={p.category}, 자격요건={p.eligibility}"
        for p in policies
    )
    profile_text = (
        f"생활 형태: {', '.join(user.living_status) or '정보 없음'}\n"
        f"필요한 도움: {', '.join(user.needed_help) or '정보 없음'}\n"
        f"주거 상황: {user.housing_situation or '정보 없음'}"
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