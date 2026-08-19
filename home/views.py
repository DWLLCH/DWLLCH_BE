import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError

from briefing.models import compute_profile_signature
from common.pagination import CommonPageNumberPagination
from common.responses import success_response

from .models import (
    Policy,
    PolicyScrap,
    CurationMatchCache,
    ProtectionType,
    AgeRange,
    IncomeCriteria,
    compute_policy_ids_hash,
)
from .serializers import (
    PolicyListSerializer,
    PolicyDetailSerializer,
    SimilarPolicySerializer,
    PolicyChatbotQuerySerializer,
    PolicyScrapSerializer,
)
from .services import get_policy_chatbot_answer, match_policies_by_condition, assess_policy_matches, GeminiRequestError

logger = logging.getLogger(__name__)

User = get_user_model()

POLICY_FILTER_GROUPS = (
    ("protectionType", "protection_types", ProtectionType),
    ("ageRange", "age_ranges", AgeRange),
    ("incomeCriteria", "income_criteria", IncomeCriteria),
)


def _parse_multi_param(request, param_name):
    raw = request.query_params.get(param_name)

    if not raw:
        return []

    return [value.strip() for value in raw.split(",") if value.strip()]


def _validate_choice_values(param_name, values, choices_cls):
    valid_values = {choice.value for choice in choices_cls}

    invalid_values = [value for value in values if value not in valid_values]

    if invalid_values:
        raise ValidationError({
            param_name: (
                f"{param_name}에 유효하지 않은 값이 있습니다: "
                f"{', '.join(invalid_values)}"
            )
        })


def _apply_policy_group_filters(queryset, request):
    """
    보호유형/연령/소득기준 필터.
    같은 그룹 내 복수 선택은 AND, 그룹 간 조건은 OR로 처리한다.
    """
    selected_groups = []

    for param_name, field_name, choices_cls in POLICY_FILTER_GROUPS:
        values = _parse_multi_param(request, param_name)

        if not values:
            continue

        _validate_choice_values(param_name, values, choices_cls)
        selected_groups.append((field_name, values))

    if not selected_groups:
        return queryset

    def matches_any_group(policy):
        for field_name, values in selected_groups:
            policy_values = set(getattr(policy, field_name) or [])
            if all(value in policy_values for value in values):
                return True
        return False

    return [policy for policy in queryset if matches_any_group(policy)]


@api_view(["GET"])
@permission_classes([AllowAny])
def policy_list(request):
    queryset = Policy.objects.all()

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    keyword = request.query_params.get("keyword")
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)

    sort = request.query_params.get("sort", "updatedAt")

    if sort == "applicationEnd":
        queryset = queryset.order_by("application_end", "-id")
    elif sort == "updatedAt":
        queryset = queryset.order_by("-updated_at", "-id")
    else:
        raise ValidationError({
            "sort": (
                "sort는 updatedAt 또는 "
                "applicationEnd 중 하나여야 합니다."
            )
        })

    queryset = _apply_policy_group_filters(queryset, request)

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)

    match_map = {}

    if (
        request.user.is_authenticated
        and request.user.profile_completed
        and page
    ):
        try:
            result = assess_policy_matches(page, request.user)

            match_map = {
                match.policy_id: match
                for match in result.matches
            }

        except GeminiRequestError:
            logger.exception(
                "Gemini policy match assessment failed: "
                "user_id=%s",
                request.user.id,
            )

    serializer = PolicyListSerializer(
        page,
        many=True,
        context={
            "match_map": match_map,
        },
    )

    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@permission_classes([AllowAny])
def policy_detail(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    match_map = {}

    if (
        request.user.is_authenticated
        and request.user.profile_completed
    ):
        try:
            result = assess_policy_matches(
                [policy],
                request.user,
            )

            match_map = {
                match.policy_id: match
                for match in result.matches
            }

        except GeminiRequestError:
            logger.exception(
                "Gemini policy detail match assessment failed: "
                "user_id=%s, policy_id=%s",
                request.user.id,
                policy.id,
            )

    serializer = PolicyDetailSerializer(policy, context={"match_map": match_map})

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

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def policy_scrap(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    if request.method == "POST":
        scrap, created = PolicyScrap.objects.get_or_create(user=request.user, policy=policy)

        if not created:
            raise ValidationError({"detail": "이미 스크랩한 정책입니다."})

        return success_response(
            data=PolicyScrapSerializer(scrap).data,
            message="정책이 스크랩되었습니다.",
            status_code=status.HTTP_201_CREATED,
        )

    scrap = get_object_or_404(PolicyScrap, user=request.user, policy=policy)

    scrap.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def policy_scrap_list(request):
    scraps = (
        PolicyScrap.objects
        .filter(user=request.user)
        .select_related("policy")
        .order_by("-created_at", "-id")
    )

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(scraps, request)

    serializer = PolicyScrapSerializer(page, many=True)

    return paginator.get_paginated_response(serializer.data)