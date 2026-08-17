import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from briefing.models import compute_profile_signature
from common.pagination import CommonPageNumberPagination
from common.responses import success_response

from .models import Policy, CurationMatchCache, compute_policy_ids_hash
from .serializers import (
    PolicyListSerializer,
    PolicyDetailSerializer,
    SimilarPolicySerializer,
    PolicyChatbotQuerySerializer,
)
from .services import get_policy_chatbot_answer, match_policies_by_condition, GeminiRequestError

logger = logging.getLogger(__name__)

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
        "bannerMessage": "자립준비청년을 위한 정책 정보를 한눈에 확인하세요.",
        "popularPolicies": PolicyListSerializer(popular_policies, many=True).data,
    }
    return success_response(
        data=data,
        message="비로그인 홈 데이터를 조회했습니다.",
    )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_curation(request):
    user = request.user

    # 1. 지역 매칭
    region_policies = Policy.objects.filter(
        Q(region_sido__isnull=True) | Q(region_sido="") | Q(region_sido=user.sido)
    ).order_by("-created_at")[:10]

    # 2. 조건 매칭 1차 필터링 
    keywords = [
        User.LivingStatus(code).label for code in (user.living_status or [])
    ] + [
        User.NeededHelp(code).label for code in (user.needed_help or [])
    ]

    housing_label = user.get_housing_type_display()
    if housing_label:
        keywords.append(housing_label)

    keywords = [k for k in keywords if k]  # 혹시 모를 빈 값/None 전부 제거

    filtered_policies = []
    if keywords:
        query = Q()
        for keyword in keywords:
            query |= Q(target_condition__icontains=keyword)
        filtered_policies = list(Policy.objects.filter(query).order_by("-created_at")[:20])

    profile_incomplete = not user.needed_help

    # 3. 캐시 조회 → 없으면 AI 호출
    condition_matched = []
    if filtered_policies:
        profile_signature = compute_profile_signature(user)
        policy_ids_hash = compute_policy_ids_hash(filtered_policies)

        cache = CurationMatchCache.objects.filter(
            profile_signature=profile_signature, policy_ids_hash=policy_ids_hash
        ).first()

        policy_map = {p.id: p for p in filtered_policies}

        if cache:
            for match in cache.matched_result:
                policy = policy_map.get(match["policy_id"])
                if policy:
                    condition_matched.append({
                        "policy": PolicyListSerializer(policy).data,
                        "matchReason": match["match_reason"],
                    })
        else:
            try:
                result = match_policies_by_condition(filtered_policies, user)
                matched_result = [
                    {"policy_id": m.policy_id, "match_reason": m.match_reason}
                    for m in result.matches
                ]
                CurationMatchCache.objects.update_or_create(
                    profile_signature=profile_signature,
                    policy_ids_hash=policy_ids_hash,
                    defaults={"matched_result": matched_result},
                )
                for match in result.matches:
                    policy = policy_map.get(match.policy_id)
                    if policy:
                        condition_matched.append({
                            "policy": PolicyListSerializer(policy).data,
                            "matchReason": match.match_reason,
                        })
            except GeminiRequestError:
                logger.exception("Gemini condition matching failed: user_id=%s", user.id)
                condition_matched = [
                    {"policy": PolicyListSerializer(p).data, "matchReason": None}
                    for p in filtered_policies[:10]
                ]

    data = {
        "userSummary": {
            "sido": user.sido,
            "sigungu": user.sigungu,
            "protectionEndDate": user.protection_end_date,
        },
        "regionMatched": PolicyListSerializer(region_policies, many=True).data,
        "conditionMatched": condition_matched,
        "hasMatch": bool(condition_matched),
        "profileIncomplete": profile_incomplete,
    }

    return success_response(
        data=data,
        message="맞춤 정책을 조회했습니다.",
    )

@api_view(["GET"])
@permission_classes([AllowAny])
def policy_similar(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    similar_policies = (
        Policy.objects.filter(category=policy.category)
        .exclude(id=policy.id)
        .order_by("-created_at")[:5]
    )

    data = {
        "similarPolicies": SimilarPolicySerializer(similar_policies, many=True).data,
    }
    return success_response(
        data=data,
        message="비슷한 정책 사례를 조회했습니다.",
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def policy_chatbot_query(request):
    serializer = PolicyChatbotQuerySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = get_policy_chatbot_answer(
            question=serializer.validated_data["question"],
            policy_id=serializer.validated_data.get("policy_id"),
        )
    except GeminiRequestError as exc:
        logger.exception("Gemini chatbot query failed")
        raise APIException(
            detail="AI 챗봇 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
            code="COMMON_500_SERVER_ERROR",
        ) from exc

    return success_response(
        data={"answer": result.answer, "answerable": result.answerable},
        message="정책 관련 질문에 답변했습니다.",
    )