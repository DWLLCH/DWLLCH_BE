from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import Briefing
from .serializers import BriefingListSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def briefing_list(request):
    category = request.query_params.get("category")
    queryset = Briefing.objects.all()

    if category:
        queryset = queryset.filter(category=category)

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = BriefingListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)