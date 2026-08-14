from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import Policy
from .serializers import PolicyListSerializer, PolicyDetailSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_list(request):
    queryset = Policy.objects.all().order_by("-created_at")

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    keyword = request.query_params.get("keyword")
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = PolicyListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_detail(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)
    serializer = PolicyDetailSerializer(policy)
    return success_response(
        data=serializer.data,
        message="정책 상세 정보를 조회했습니다.",
    )

@api_view(["GET"])
@permission_classes([AllowAny])
def home_guest(request):
    popular_policies = Policy.objects.all().order_by("-created_at")[:5]

    data = {
        "banner_message": "자립준비청년을 위한 정책 정보를 한눈에 확인하세요.",
        "popular_policies": PolicyListSerializer(popular_policies, many=True).data,
    }
    return Response(data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_curation(request):
    user = request.user

    keywords = [
        User.LivingStatus(code).label for code in user.living_status
    ] + [
        User.NeededHelp(code).label for code in user.needed_help
    ]
    keywords.append(user.get_housing_type_display())

    query = Q()
    for keyword in keywords:
        query |= Q(target_condition__icontains=keyword)

    policies = Policy.objects.filter(query).order_by("-created_at")[:10]

    data = {
        "user_summary": {
            "sido": user.sido,
            "sigungu": user.sigungu,
            "protection_end_date": user.protection_end_date,
        },
        "curated_policies": PolicyListSerializer(policies, many=True).data,
    }
    return Response(data, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([AllowAny])
def policy_chatbot_query(request):
    serializer = PolicyChatbotQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        answer = get_policy_chatbot_answer(
            question=serializer.validated_data["question"],
            policy_id=serializer.validated_data.get("policy_id"),
        )
    except Exception:
        return Response(
            {"detail": "챗봇 응답 생성 중 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"answer": answer}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_similar(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    similar_policies = (
        Policy.objects.filter(category=policy.category)
        .exclude(id=policy.id)
        .order_by("-created_at")[:5]
    )

    serializer = SimilarPolicySerializer(similar_policies, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)