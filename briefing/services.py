import json

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors, types
from pydantic import BaseModel, Field, ValidationError


class BriefingSummaryResult(BaseModel):
    bullets: list[str] = Field(default_factory=list)


class GeminiRequestError(Exception):
    """Gemini API 또는 네트워크 호출 실패."""


BRIEFING_SUMMARY_PROMPT = """
당신은 자립준비청년을 위한 정책/금융 정보를 요약하는 한국어 지원 챗봇입니다.

다음 정책을 반드시 지키세요.

1. 아래 "팩트" 목록에 있는 내용만 사용해서 요약을 작성하세요.
2. 팩트에 없는 금액, 조건, 날짜, 기관명을 새로 만들어내지 마세요.
3. 팩트 목록에 없는 내용이 필요하면 그 항목은 생략하세요.
4. 3~4개의 짧은 불릿 문장으로 작성하세요. 한 문장은 40자 이내로 작성하세요.
5. 사용자 상황에 맞는 어투로 자연스럽게 재구성하되, 사실 관계는 절대 바꾸지 마세요.
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


def generate_briefing_summary(source_facts, user):
    client = _get_client()

    facts_text = "\n".join(f"- {fact}" for fact in source_facts)
    profile_text = (
        f"생활 형태: {', '.join(user.living_status) or '정보 없음'}\n"
        f"필요한 도움: {', '.join(user.needed_help) or '정보 없음'}\n"
        f"주거 상황: {user.housing_situation or '정보 없음'}"
    )

    prompt = f"""
{BRIEFING_SUMMARY_PROMPT}

팩트:
{facts_text}

사용자 상황:
{profile_text}
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BriefingSummaryResult,
            ),
        )
    except (genai_errors.APIError, httpx.HTTPError, TimeoutError) as exc:
        raise GeminiRequestError from exc

    try:
        return _parse_response(response, BriefingSummaryResult)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiRequestError from exc