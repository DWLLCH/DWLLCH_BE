from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    status_code = response.status_code
    custom_code = getattr(exc, "api_code", None)

    if custom_code:
        if isinstance(response.data, dict):
            detail = response.data.get("detail", str(exc))
        else:
            detail = str(exc)
        response.data = {
            "success": False,
            "code": custom_code,
            "message": str(detail),
            "data": None,
        }
        return response

    if status_code == 401:
        code = "AUTH_401_UNAUTHORIZED"
        message = "인증이 필요합니다."

    elif status_code == 403:
        code = "AUTH_403_FORBIDDEN"
        message = "접근 권한이 없습니다."

    elif status_code == 404:
        code = "COMMON_404_NOT_FOUND"
        message = "요청한 리소스를 찾을 수 없습니다."

    elif status_code == 400:
        code = "COMMON_400_INVALID_INPUT"
        message = "요청 값이 올바르지 않습니다."

    else:
        code = "COMMON_500_SERVER_ERROR"
        message = "서버 내부 오류가 발생했습니다."

    data = response.data if status_code == 400 else None

    response.data = {
        "success": False,
        "code": code,
        "message": message,
        "data": data,
    }

    return response
