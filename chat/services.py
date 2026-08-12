import json
from typing import Literal

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ExternalAppLink(BaseModel):
    name: str
    url: str


class RiskAnalysisResult(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    summary: str
    flagged_clauses: list[str] = Field(default_factory=list)
    missing_verifications: list[str] = Field(default_factory=list)
    action_guide: list[str] = Field(default_factory=list)
    external_app_link: ExternalAppLink | None = None
    reply: str
    suggested_replies: list[str] = Field(default_factory=list)
    image_readable: bool = True


class StructuredReportResult(BaseModel):
    date: str = ""
    amount: str = ""
    location: str = ""
    counterpart: str = ""
    situation_summary: str = ""
    risk_type: str = ""
    risk_grade: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    missing_fields: list[str] = Field(default_factory=list)


RISK_ANALYSIS_PROMPT = """
당신은 청년의 주거·금융·계약·범죄피해 위험 신호를 판독하는 한국어 지원 챗봇입니다.

다음 정책을 반드시 지키세요.

1. 법률가처럼 사기 여부나 범죄 여부를 확정하지 마세요.
2. "사기입니다", "불법입니다"처럼 단정하지 말고
   "의심 신호가 있습니다", "확인이 필요합니다", "전문가 상담을 권장합니다"
   같은 표현을 사용하세요.
3. 사용자의 불안을 과도하게 키우지 말고, 짧고 구체적인 행동 지침을 주세요.
4. 이미지가 흐리거나 핵심 내용을 읽을 수 없다면 image_readable=false로 반환하세요.
5. 이미지가 읽히지 않으면 추측해서 분석하지 마세요.
6. 위험도 기준:
   - LOW: 일반적인 정보 질문 또는 뚜렷한 위험 신호 없음
   - MEDIUM: 추가 확인이 필요한 불확실한 신호
   - HIGH: 금전 손실, 계약 피해, 사기 의심 등 즉시 확인이나 중단을 권고할 상황
   - CRITICAL: 자해·타해 위험, 현재 진행 중인 심각한 폭력 또는 즉각적인 신체 위험
7. CRITICAL은 단순 계약 분쟁이나 금전 손실에 사용하지 마세요.
8. reply는 모바일 채팅 화면에 표시할 자연스러운 한국어 답변으로 작성하세요.
9. suggested_replies에는 사용자가 다음에 선택할 수 있는 짧은 답변을 최대 3개 작성하세요.
10. 사용자가 제공하지 않은 날짜, 금액, 장소, 상대방 정보를 만들어내지 마세요.
11. flagged_clauses에는 계약서나 대화에서 발견된 의심 문구만 넣으세요.
12. external_app_link는 실제로 도움이 되는 경우에만 반환하세요.
"""


STRUCTURE_PROMPT = """
아래 대화 내역을 SOS 전달용 6개 항목으로 구조화하세요.

항목:
- date: 사건 또는 계약 날짜
- amount: 피해 또는 계약 금액
- location: 사건 또는 주거지 위치
- counterpart: 상대방 또는 기관
- situation_summary: 객관적인 상황 요약
- risk_type: 위험 유형

규칙:
1. 대화에 없는 사실을 추측하지 마세요.
2. 확인되지 않은 항목은 빈 문자열로 반환하세요.
3. 빈 항목의 영문 필드명을 missing_fields에 넣으세요.
4. 법적 결론이나 범죄 확정 표현을 사용하지 마세요.
5. risk_grade는 LOW, MEDIUM, HIGH, CRITICAL 중 하나입니다.
6. CRITICAL은 즉각적인 신체 위험, 자해·타해 또는 현재 진행 중인 심각한
   범죄피해 위험에만 사용하세요.
"""


def _get_client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_response(response, schema):
    if getattr(response, "parsed", None):
        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        return schema.model_validate(parsed)

    return schema.model_validate(json.loads(response.text))


def _format_history(messages):
    formatted = []

    for message in messages:
        sender = "사용자" if message.sender == "USER" else "AI 챗봇"
        content = message.content or "(이미지 첨부)"

        formatted.append(f"{sender}: {content}")

    return "\n".join(formatted)


def analyze_risk(content, uploaded_file=None, previous_messages=None):
    client = _get_client()
    history = _format_history(previous_messages or [])

    prompt = f"""
{RISK_ANALYSIS_PROMPT}

이전 대화:
{history or "이전 대화 없음"}

현재 사용자 입력:
{content or "텍스트 설명 없이 이미지만 첨부됨"}

현재 사용자 입력과 이전 대화의 맥락을 함께 분석하세요.
"""

    contents = [prompt]

    if uploaded_file:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        contents.append(
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=uploaded_file.content_type,
            )
        )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RiskAnalysisResult,
        ),
    )

    return _parse_response(response, RiskAnalysisResult)


def structure_session(messages):
    client = _get_client()
    history = _format_history(messages)

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=f"""
{STRUCTURE_PROMPT}

대화 내역:
{history}
""",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StructuredReportResult,
        ),
    )

    return _parse_response(response, StructuredReportResult)