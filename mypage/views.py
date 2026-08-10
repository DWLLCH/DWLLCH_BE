from datetime import date

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import MypageStatusSerializer, ProfileSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mypage_status(request):
    user = request.user
    d_day = (user.protection_end_date - date.today()).days

    data = {
        "protection_end_date": user.protection_end_date,
        "d_day": d_day,
    }
    serializer = MypageStatusSerializer(data)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def mypage_profile(request):
    user = request.user

    if request.method == "GET":
        serializer = ProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = ProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)