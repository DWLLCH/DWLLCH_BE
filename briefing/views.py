import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import Briefing, BriefingSummaryCache, compute_profile_signature
from .serializers import BriefingListSerializer, BriefingDetailSerializer
from .services import GeminiRequestError, generate_briefing_summary

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def briefing_list(request):
    category = request.query_params.get("category")
    user = request.user

    queryset = Briefing.objects.all()

    if category:
        queryset = queryset.filter(category=category)

    briefings = list(queryset)

    category_priority = _get_category_priority(user)
    briefings.sort(key=lambda b: category_priority.get(b.category, 99))

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(briefings, request)
    serializer = BriefingListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def briefing_detail(request, briefing_id):
    briefing = get_object_or_404(Briefing, id=briefing_id)
    user = request.user

    signature = compute_profile_signature(user)
    cache = BriefingSummaryCache.objects.filter(
        briefing=briefing, profile_signature=signature
    ).first()

    if cache:
        bullets = cache.generated_summary.get("bullets", [])
    else:
        try:
            result = generate_briefing_summary(briefing.source_facts, user)
            bullets = result.bullets
            BriefingSummaryCache.objects.update_or_create(
                briefing=briefing,
                profile_signature=signature,
                defaults={"generated_summary": {"bullets": bullets}},
            )
        except GeminiRequestError:
            logger.exception(
                "Gemini briefing summary failed: briefing_id=%s", briefing.id
            )
            bullets = [briefing.card_summary]

    serializer = BriefingDetailSerializer(
        briefing, context={"key_summary_bullets": bullets}
    )
    return success_response(
        data=serializer.data,
        message="브리핑 상세 정보를 조회했습니다.",
    )