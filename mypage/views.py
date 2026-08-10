from datetime import date

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import MypageStatusSerializer, ProfileSerializer

from rest_framework.generics import get_object_or_404

from .models import Application
from .serializers import ApplicationSerializer, ApplicationStatusUpdateSerializer



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

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def application_list(request):
    if request.method == "GET":
        applications = Application.objects.filter(user=request.user).order_by("-created_at")
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = ApplicationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def application_delete(request, application_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    application.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def application_status_update(request, application_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    serializer = ApplicationStatusUpdateSerializer(
        application, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)