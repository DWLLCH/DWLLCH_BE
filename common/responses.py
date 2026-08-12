from rest_framework import status
from rest_framework.response import Response


def success_response(
    data=None,
    message="요청이 정상 처리되었습니다.",
    code="SUCCESS",
    status_code=status.HTTP_200_OK,
):
    return Response(
        {
            "success": True,
            "code": code,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status_code,
    )