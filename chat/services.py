from dataclasses import dataclass


@dataclass
class RiskAnalysisResult:
    risk_level: str | None = None
    raw_response: dict | None = None


def analyze_risk(content: str) -> RiskAnalysisResult:
    """
    AI 위기도 분석 진입점.
    AI API 확정 전까지는 항상 미판독 상태를 반환한다.
    확정 후 이 함수 내부만 교체하면 된다.
    """
    return RiskAnalysisResult(risk_level=None, raw_response=None)