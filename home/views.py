import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError
from datetime import timedelta
from django.utils import timezone
from briefing.models import compute_profile_signature
from common.pagination import CommonPageNumberPagination
from common.responses import success_response
from django.db.models import Count

from .models import (
    Policy,
    PolicyScrap,
    CurationMatchCache,
    PolicyMatchCache,
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
CACHE_VALID_DURATION = timedelta(days=1)

# AI 추천순 정렬 우선순위. 매칭 결과가 없는 정책은 맨 뒤로 보낸다.
MATCH_LEVEL_SORT_PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
UNMATCHED_SORT_PRIORITY = len(MATCH_LEVEL_SORT_PRIORITY)

POLICY_SORT_OPTIONS = ("updatedAt", "applicationEnd", "scrapCount", "matchLevel")


def _assess_matches_safely(policies, user):
    """매칭 실패는 목록 조회 자체를 막지 않는다. 실패하면 빈 결과로 본다."""
    try:
        return get_or_assess_policy_matches(policies, user)
    except GeminiRequestError:
        logger.exception(
            "Gemini policy match assessment failed: user_id=%s",
            user.id,
        )
        return {}


def get_or_assess_policy_matches(policies, user):
    """정책 단위로 캐시를 재사용하고, 캐시에 없는 정책만 AI 에 묻는다.

    정책 집합 단위로 캐싱하면 정렬/필터가 바뀌거나 목록에서 상세로 넘어갈 때
    집합이 달라져 캐시가 통째로 빗나간다. 정책 하나씩 캐시를 두면
    이미 평가한 정책은 그대로 쓰고 처음 보는 정책만 호출 대상이 된다.
    """
    if not policies:
        return {}

    profile_signature = compute_profile_signature(user)
    cutoff = timezone.now() - CACHE_VALID_DURATION

    match_map = {
        cache.policy_id: {
            "policy_id": cache.policy_id,
            "match_level": cache.match_level,
            "match_reason": cache.match_reason,
        }
        for cache in PolicyMatchCache.objects.filter(
            profile_signature=profile_signature,
            policy__in=policies,
            updated_at__gte=cutoff,
        )
    }

    missing = [policy for policy in policies if policy.id not in match_map]

    if not missing:
        return match_map

    result = assess_policy_matches(missing, user)
    missing_ids = {policy.id for policy in missing}

    for match in result.matches:
        # 물어보지 않은 정책 id 를 돌려주는 경우가 있어 걸러낸다.
        if match.policy_id not in missing_ids:
            continue

        PolicyMatchCache.objects.update_or_create(
            policy_id=match.policy_id,
            profile_signature=profile_signature,
            defaults={
                "match_level": match.match_level,
                "match_reason": match.match_reason,
            },
        )
        match_map[match.policy_id] = {
            "policy_id": match.policy_id,
            "match_level": match.match_level,
            "match_reason": match.match_reason,
        }

    return match_map

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
    정책 쪽 값이 비어 있으면 해당 조건에 제한이 없다는 뜻이므로 항상 매칭한다.
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

            # 대상이 지정되지 않은 정책 = 해당 조건에 제한이 없는 정책
            if not policy_values:
                return True

            if all(value in policy_values for value in values):
                return True
        return False

    return [policy for policy in queryset if matches_any_group(policy)]

@api_view(["GET"])
@permission_classes([AllowAny])
def policy_list(request):
    queryset = Policy.objects.annotate(scrap_count=Count("scraps"))

    category = request.query_params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    keyword = request.query_params.get("keyword")
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)

    sort = request.query_params.get("sort", "updatedAt")

    if sort not in POLICY_SORT_OPTIONS:
        raise ValidationError({
            "sort": f"sort는 {', '.join(POLICY_SORT_OPTIONS)} 중 하나여야 합니다."
        })

    if sort == "applicationEnd":
        queryset = queryset.order_by("application_end", "-id")
    elif sort == "scrapCount":
        queryset = queryset.order_by("-scrap_count", "-id")
    else:
        # matchLevel 도 최신순을 기본 순서로 깔고, 아래에서 매칭 등급으로 다시 정렬한다.
        queryset = queryset.order_by("-updated_at", "-id")

    queryset = _apply_policy_group_filters(queryset, request)

    can_match = (
        request.user.is_authenticated
        and request.user.profile_completed
    )

    match_map = {}

    if sort == "matchLevel" and can_match:
        # 매칭 등급은 페이지가 잘린 뒤에는 알 수 없으므로,
        # 필터된 전체를 먼저 평가하고 정렬한 다음 페이지를 자른다.
        policies = list(queryset)
        match_map = _assess_matches_safely(policies, request.user)

        # sorted 는 안정 정렬이라 같은 등급 안에서는 위의 기본 순서가 유지된다.
        queryset = sorted(
            policies,
            key=lambda policy: MATCH_LEVEL_SORT_PRIORITY.get(
                (match_map.get(policy.id) or {}).get("match_level"),
                UNMATCHED_SORT_PRIORITY,
            ),
        )

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)

    if not match_map and can_match and page:
        match_map = _assess_matches_safely(page, request.user)

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
            match_map = get_or_assess_policy_matches([policy], request.user)
        except GeminiRequestError:
            logger.exception(
                "Gemini policy detail match assessment failed: user_id=%s, policy_id=%s",
                request.user.id, policy.id,
            )

    serializer = PolicyDetailSerializer(
        policy,
        context={"request": request, "match_map": match_map},
    )

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
            cache_type=CurationMatchCache.CacheType.CURATION,
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
                    cache_type=CurationMatchCache.CacheType.CURATION,
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

    match_map = {}

    if request.user.profile_completed and page:
        match_map = _assess_matches_safely(
            [scrap.policy for scrap in page],
            request.user,
        )

    serializer = PolicyScrapSerializer(
        page,
        many=True,
        context={
            "match_map": match_map,
        },
    )

    return paginator.get_paginated_response(serializer.data)