from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    if response.status_code == 401:
        detail = response.data.get("detail", "")

        if "expired" in str(detail).lower():
            code = "AUTH_401_EXPIRED_TOKEN"
            message = "Access Token이 만료되었습니다."
        else:
            code = "AUTH_401_UNAUTHORIZED"
            message = "인증이 필요합니다."

    elif response.status_code == 403:
        code = "AUTH_403_FORBIDDEN"
        message = "접근 권한이 없습니다."

    elif response.status_code == 404:
        code = "COMMON_404_NOT_FOUND"
        message = "요청한 리소스를 찾을 수 없습니다."

    elif response.status_code == 400:
        code = "COMMON_400_INVALID_INPUT"
        message = "요청 값이 올바르지 않습니다."

    else:
        code = "COMMON_500_SERVER_ERROR"
        message = "서버 내부 오류가 발생했습니다."

    response.data = {
        "success": False,
        "code": code,
        "message": message,
        "data": None,
    }

    return response