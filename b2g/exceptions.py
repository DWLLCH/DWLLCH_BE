from rest_framework.exceptions import APIException


class LicenseRequired(APIException):
    status_code = 402
    default_detail = "기관 라이선스가 비활성 상태입니다."
    default_code = "B2G_402_LICENSE_REQUIRED"
    api_code = "B2G_402_LICENSE_REQUIRED"


class InvalidDashboardParameter(APIException):
    status_code = 400
    default_detail = "조회 조건이 올바르지 않습니다."
    default_code = "COMMON_400_INVALID_INPUT"
    api_code = "COMMON_400_INVALID_INPUT"