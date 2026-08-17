from rest_framework.exceptions import APIException


class BriefingAPIException(APIException):
    status_code = 400
    api_code = "BRIEFING_400_INVALID_REQUEST"
    default_detail = "요청을 처리할 수 없습니다."


class GeminiServiceUnavailableException(BriefingAPIException):
    status_code = 503
    api_code = "BRIEFING_503_AI_SERVICE_UNAVAILABLE"
    default_detail = "AI 요약 생성 서비스에 일시적인 문제가 발생했습니다."