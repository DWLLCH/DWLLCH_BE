from rest_framework.exceptions import APIException


class ChatAPIException(APIException):
    status_code = 400
    api_code = "CHAT_400_INVALID_REQUEST"
    default_detail = "요청을 처리할 수 없습니다."


class ImageUnreadableException(ChatAPIException):
    status_code = 422
    api_code = "CHAT_422_IMAGE_UNREADABLE"
    default_detail = "이미지를 다시 촬영하거나 텍스트로 입력해주세요"


class ConsentRequiredException(ChatAPIException):
    status_code = 400
    api_code = "CHAT_400_CONSENT_REQUIRED"
    default_detail = "연계를 위해서는 동의가 필요합니다"


class GeminiServiceUnavailableException(ChatAPIException):
    status_code = 503
    api_code = "CHAT_503_AI_SERVICE_UNAVAILABLE"
    default_detail = "AI 분석 서비스에 일시적인 문제가 발생했습니다."


class AlreadyReportedException(ChatAPIException):
    status_code = 400
    api_code = "CHAT_400_ALREADY_REPORTED"
    default_detail = "이미 신고한 AI 판독 결과입니다."
