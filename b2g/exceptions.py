from rest_framework.exceptions import APIException


class B2GPermissionDeniedException(APIException):
    status_code = 403
    api_code = "AUTH_403_FORBIDDEN"
    default_detail = "전담기관 관리자 권한이 필요합니다."


class B2GLicenseRequiredException(APIException):
    status_code = 402
    api_code = "B2G_402_LICENSE_REQUIRED"
    default_detail = "기관 라이선스가 비활성 상태입니다."