import math
from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from b2g.models import ConsultRequest
from b2g.permissions import IsOrganizationAdmin
from b2g.serializers import (
    ConsultRequestDetailSerializer,
    ConsultRequestListSerializer,
)
from common.responses import success_response


URGENCY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


class DashboardBaseView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsOrganizationAdmin,
    ]

    def get_queryset(self, request):
        return ConsultRequest.objects.filter(
            organization=request.organization,
            linkage_consented=True,
        )


class ConsultRequestListView(DashboardBaseView):
    def get(self, request):
        queryset = self.get_queryset(request)

        urgency_level = request.query_params.get("urgencyLevel")
        request_status = request.query_params.get("status")

        if urgency_level:
            if urgency_level not in ConsultRequest.UrgencyLevel.values:
                raise serializers.ValidationError(
                    {"urgencyLevel": "올바르지 않은 시급성입니다."}
                )
            queryset = queryset.filter(
                urgency_level=urgency_level
            )

        if request_status:
            if request_status not in ConsultRequest.Status.values:
                raise serializers.ValidationError(
                    {"status": "올바르지 않은 상태입니다."}
                )
            queryset = queryset.filter(status=request_status)

        try:
            page = int(request.query_params.get("page", 0))
            size = int(request.query_params.get("size", 20))
        except ValueError:
            raise serializers.ValidationError(
                {"pagination": "page와 size는 숫자여야 합니다."}
            )

        if page < 0 or size < 1 or size > 100:
            raise serializers.ValidationError(
                {
                    "pagination": (
                        "page는 0 이상, size는 1~100이어야 합니다."
                    )
                }
            )

        sort = request.query_params.get(
            "sort",
            "urgencyLevel,desc",
        )

        urgency_case = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }

        from django.db.models import Case, IntegerField, Value, When

        queryset = queryset.annotate(
            urgency_order=Case(
                *[
                    When(
                        urgency_level=level,
                        then=Value(order),
                    )
                    for level, order in urgency_case.items()
                ],
                default=Value(0),
                output_field=IntegerField(),
            )
        )

        allowed_sorts = {
            "urgencyLevel,desc": (
                "-urgency_order",
                "-received_at",
                "-id",
            ),
            "urgencyLevel,asc": (
                "urgency_order",
                "-received_at",
                "-id",
            ),
            "receivedAt,desc": (
                "-received_at",
                "-id",
            ),
            "receivedAt,asc": (
                "received_at",
                "id",
            ),
        }

        if sort not in allowed_sorts:
            raise serializers.ValidationError(
                {"sort": "지원하지 않는 정렬 조건입니다."}
            )

        queryset = queryset.order_by(*allowed_sorts[sort])

        total_elements = queryset.count()
        total_pages = (
            math.ceil(total_elements / size)
            if total_elements
            else 0
        )

        start = page * size
        end = start + size
        items = queryset[start:end]

        serializer = ConsultRequestListSerializer(
            items,
            many=True,
        )

        return success_response(
            data={
                "content": serializer.data,
                "page": page,
                "size": size,
                "totalElements": total_elements,
                "totalPages": total_pages,
                "hasNext": page + 1 < total_pages,
            }
        )


class ConsultRequestDetailView(DashboardBaseView):
    def get(self, request, request_id):
        consult_request = get_object_or_404(
            self.get_queryset(request),
            id=request_id,
        )

        serializer = ConsultRequestDetailSerializer(
            consult_request
        )
        return success_response(data=serializer.data)


class DashboardStatsView(DashboardBaseView):
    GROUP_BY_FUNCTIONS = {
        "DAY": TruncDay,
        "WEEK": TruncWeek,
        "MONTH": TruncMonth,
    }

    def get(self, request):
        queryset = self.get_queryset(request)

        today = timezone.localdate()
        default_from = today.replace(day=1)

        from_date = parse_date(
            request.query_params.get(
                "from",
                default_from.isoformat(),
            )
        )
        to_date = parse_date(
            request.query_params.get(
                "to",
                today.isoformat(),
            )
        )
        group_by = request.query_params.get("groupBy", "DAY")

        if from_date is None or to_date is None:
            raise serializers.ValidationError(
                {"period": "날짜 형식은 YYYY-MM-DD여야 합니다."}
            )

        if from_date > to_date:
            raise serializers.ValidationError(
                {"period": "조회 시작일은 종료일보다 늦을 수 없습니다."}
            )

        if group_by not in self.GROUP_BY_FUNCTIONS:
            raise serializers.ValidationError(
                {"groupBy": "DAY, WEEK, MONTH 중 하나여야 합니다."}
            )

        queryset = queryset.filter(
            received_at__date__gte=from_date,
            received_at__date__lte=to_date,
        )

        resolved_statuses = [
            ConsultRequest.Status.RESOLVED,
            ConsultRequest.Status.CLOSED,
        ]

        response_duration = ExpressionWrapper(
            F("assigned_at") - F("received_at"),
            output_field=DurationField(),
        )


        # SQLite를 포함한 DB 호환성을 위해 조건 집계는 별도 count 사용
        total_requests = queryset.count()
        critical_requests = queryset.filter(
            urgency_level=ConsultRequest.UrgencyLevel.CRITICAL
        ).count()
        high_requests = queryset.filter(
            urgency_level=ConsultRequest.UrgencyLevel.HIGH
        ).count()
        resolved_requests = queryset.filter(
            status__in=resolved_statuses
        ).count()

        average_duration = (
            queryset
            .exclude(assigned_at=None)
            .aggregate(value=Avg(response_duration))["value"]
        )
        average_minutes = (
            round(average_duration.total_seconds() / 60)
            if average_duration
            else 0
        )

        by_risk_type = list(
            queryset
            .values("risk_type")
            .annotate(count=Count("id"))
            .order_by("-count", "risk_type")
        )

        by_urgency_level = list(
            queryset
            .values("urgency_level")
            .annotate(count=Count("id"))
            .order_by("-count", "urgency_level")
        )

        trunc_function = self.GROUP_BY_FUNCTIONS[group_by]

        trend_rows = (
            queryset
            .annotate(period=trunc_function("received_at"))
            .values("period")
            .annotate(
                request_count=Count("id"),
            )
            .order_by("period")
        )

        trend = []

        for row in trend_rows:
            period = row["period"]
            next_period = self.get_next_period(period, group_by)

            resolved_count = queryset.filter(
                resolved_at__gte=period,
                resolved_at__lt=next_period,
                status__in=resolved_statuses,
            ).count()

            trend.append(
                {
                    "date": period.date(),
                    "requestCount": row["request_count"],
                    "resolvedCount": resolved_count,
                }
            )

        return success_response(
            data={
                "period": {
                    "from": from_date,
                    "to": to_date,
                },
                "summary": {
                    "totalRequests": total_requests,
                    "criticalRequests": critical_requests,
                    "highRequests": high_requests,
                    "resolvedRequests": resolved_requests,
                    "averageResponseMinutes": average_minutes,
                },
                "byRiskType": [
                    {
                        "riskType": row["risk_type"],
                        "count": row["count"],
                    }
                    for row in by_risk_type
                ],
                "byUrgencyLevel": [
                    {
                        "urgencyLevel": row["urgency_level"],
                        "count": row["count"],
                    }
                    for row in by_urgency_level
                ],
                "trend": trend,
            }
        )

    def get_next_period(self, period, group_by):
        if group_by == "DAY":
            return period + timedelta(days=1)

        if group_by == "WEEK":
            return period + timedelta(days=7)

        if period.month == 12:
            return period.replace(
                year=period.year + 1,
                month=1,
            )

        return period.replace(month=period.month + 1)