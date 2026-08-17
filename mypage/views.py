from datetime import date

from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import Application, ChecklistItem, Notification
from .serializers import (
    MypageStatusSerializer,
    ProfileSerializer,
    ApplicationSerializer,
    ApplicationStatusUpdateSerializer,
    ChecklistItemSerializer,
    NotificationSerializer,
)

from users.serializers import OnboardingProfileSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mypage_status(request):
    user = request.user

    if user.protection_end_date:
        d_day = (user.protection_end_date - date.today()).days
    else:
        d_day = None

    serializer = MypageStatusSerializer({
        "protection_end_date": user.protection_end_date,
        "d_day": d_day,
    })
    return success_response(
        data=serializer.data,
        message="보호종료 상태를 조회했습니다.",
    )


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated])
def mypage_profile(request):
    user = request.user

    if request.method == "GET":
        serializer = ProfileSerializer(user)
        return success_response(
            data=serializer.data,
            message="프로필 정보를 조회했습니다.",
        )

    if request.method == "POST":
        with transaction.atomic():
            user = User.objects.select_for_update().get(
                pk=request.user.pk
            )

            if user.profile_completed:
                return Response(
                    {
                        "success": False,
                        "code": "PROFILE_409_ALREADY_COMPLETED",
                        "message": "이미 자립 프로필이 등록되어 있습니다.",
                        "data": None,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            serializer = OnboardingProfileSerializer(
                user,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return success_response(
                data=serializer.data,
                message="자립 프로필이 등록되었습니다.",
                status_code=status.HTTP_201_CREATED,
            )

    serializer = ProfileSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return success_response(
        data=serializer.data,
        message="프로필 정보가 수정되었습니다.",
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def application_list(request):
    if request.method == "GET":
        applications = Application.objects.filter(user=request.user).order_by("-created_at")
        paginator = CommonPageNumberPagination()
        page = paginator.paginate_queryset(applications, request)
        serializer = ApplicationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = ApplicationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    application = serializer.save(user=request.user)
    return success_response(
        data=ApplicationSerializer(application).data,
        message="신청 항목이 등록되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


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
    serializer = ApplicationStatusUpdateSerializer(application, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return success_response(
        data=serializer.data,
        message="신청 상태가 변경되었습니다.",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def checklist_list(request, application_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    items = application.checklist_items.all()
    serializer = ChecklistItemSerializer(items, many=True)
    return success_response(
        data={"items": serializer.data},
        message="준비항목 체크리스트를 조회했습니다.",
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def checklist_item_update(request, application_id, item_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    item = get_object_or_404(ChecklistItem, id=item_id, application=application)

    serializer = ChecklistItemSerializer(item, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return success_response(
        data=serializer.data,
        message="체크리스트 항목이 수정되었습니다.",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(notifications, request)
    serializer = NotificationSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)