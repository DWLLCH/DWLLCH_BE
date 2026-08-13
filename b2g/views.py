import math
from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from b2g.exceptions import InvalidDashboardParameter, LicenseRequired
from b2g.models import ConsultRequest
from b2g.permissions import IsOrganizationAdmin
from b2g.serializers import (
    ConsultRequestDetailSerializer,
    ConsultRequestListSerializer,
)


def success_response(data, message="요청이 정상 처리되었습니다.", status_code=200):
    return Response(
        {
            "success": True,
            "code": "SUCCESS",
            "message": message,
            "data": data,
        },
        status=status_code,
    )


class DashboardBaseView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if not request.organization.license_active:
            raise LicenseRequired()


class ConsultRequestListView(DashboardBaseView):
    def get(self, request):
        queryset = (
            ConsultRequest.objects
            .filter(
                organization=request.organization,
                linkage_consented=True,
            )
            .select_related("requester")
        )

        urgency_level = request.query_params.get("urgencyLevel")
        request_status = request.query_params.get("status")

        if urgency_level:
            valid_urgencies = {
                choice[0] for choice in ConsultRequest.UrgencyLevel.choices
            }

            if urgency_level not in valid_urgencies:
                raise InvalidDashboardParameter(
                    "urgencyLevel 값이 올바르지 않습니다."
                )

            queryset = queryset.filter(urgency_level=urgency_level)

        if request_status:
            valid_statuses = {
                choice[0] for choice in ConsultRequest.Status.choices
            }

            if request_status not in valid_statuses:
                raise InvalidDashboardParameter(
                    "status 값이 올바르지 않습니다."
                )

            queryset = queryset.filter(status=request_status)

        try:
            page = int(request.query_params.get("page", 0))
            size = int(request.query_params.get("size", 20))
        except (TypeError, ValueError):
            raise InvalidDashboardParameter(
                "page와 size는 정수여야 합니다."
            )

        if page < 0 or size < 1 or size > 100:
            raise InvalidDashboardParameter(
                "page는 0 이상, size는 1 이상 100 이하여야 합니다."
            )

        sort = request.query_params.get("sort", "urgencyLevel,desc")
        queryset = self._apply_sort(queryset, sort)

        total_elements = queryset.count()
        total_pages = math.ceil(total_elements / size) if total_elements else 0

        start = page * size
        end = start + size
        page_queryset = queryset[start:end]

        serializer = ConsultRequestListSerializer(
            page_queryset,
            many=True,
        )

        return success_response(
            {
                "content": serializer.data,
                "page": page,
                "size": size,
                "totalElements": total_elements,
                "totalPages": total_pages,
                "hasNext": page + 1 < total_pages,
            }
        )

    def _apply_sort(self, queryset, sort):
        try:
            field_name, direction = sort.split(",", maxsplit=1)
        except ValueError:
            raise InvalidDashboardParameter(
                "sort는 '필드,asc' 또는 '필드,desc' 형식이어야 합니다."
            )

        if direction not in {"asc", "desc"}:
            raise InvalidDashboardParameter(
                "정렬 방향은 asc 또는 desc만 사용할 수 있습니다."
            )

        field_map = {
            "urgencyLevel": "urgency_rank",
            "receivedAt": "received_at",
            "status": "status",
        }

        if field_name not in field_map:
            raise InvalidDashboardParameter(
                "지원하지 않는 정렬 필드입니다."
            )

        if field_name == "urgencyLevel":
            from django.db.models import Case, IntegerField, Value, When

            queryset = queryset.annotate(
                urgency_rank=Case(
                    When(
                        urgency_level=ConsultRequest.UrgencyLevel.CRITICAL,
                        then=Value(4),
                    ),
                    When(
                        urgency_level=ConsultRequest.UrgencyLevel.HIGH,
                        then=Value(3),
                    ),
                    When(
                        urgency_level=ConsultRequest.UrgencyLevel.MEDIUM,
                        then=Value(2),
                    ),
                    When(
                        urgency_level=ConsultRequest.UrgencyLevel.LOW,
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )

        database_field = field_map[field_name]

        if direction == "desc":
            database_field = f"-{database_field}"

        return queryset.order_by(database_field, "-received_at")


class ConsultRequestDetailView(DashboardBaseView):
    def get(self, request, request_id):
        consult_request = (
            ConsultRequest.objects
            .filter(
                id=request_id,
                organization=request.organization,
                linkage_consented=True,
            )
            .select_related("requester")
            .first()
        )

        if consult_request is None:
            return Response(
                {
                    "success": False,
                    "code": "COMMON_404_NOT_FOUND",
                    "message": "상담요청을 찾을 수 없습니다.",
                    "data": None,
                },
                status=404,
            )

        serializer = ConsultRequestDetailSerializer(consult_request)
        return success_response(serializer.data)


class DashboardStatsView(DashboardBaseView):
    GROUP_FUNCTIONS = {
        "DAY": TruncDay,
        "WEEK": TruncWeek,
        "MONTH": TruncMonth,
    }

    def get(self, request):
        from_date, to_date, group_by = self._validate_parameters(request)

        queryset = ConsultRequest.objects.filter(
            organization=request.organization,
            linkage_consented=True,
            received_at__date__gte=from_date,
            received_at__date__lte=to_date,
        )

        total_requests = queryset.count()
        critical_requests = queryset.filter(
            urgency_level=ConsultRequest.UrgencyLevel.CRITICAL
        ).count()
        high_requests = queryset.filter(
            urgency_level=ConsultRequest.UrgencyLevel.HIGH
        ).count()
        resolved_requests = queryset.filter(
            status__in=[
                ConsultRequest.Status.RESOLVED,
                ConsultRequest.Status.CLOSED,
            ]
        ).count()

        response_duration = ExpressionWrapper(
            F("first_responded_at") - F("received_at"),
            output_field=DurationField(),
        )

        average_duration = (
            queryset
            .filter(first_responded_at__isnull=False)
            .aggregate(average=Avg(response_duration))
            .get("average")
        )

        average_response_minutes = None
        if average_duration is not None:
            average_response_minutes = round(
                average_duration.total_seconds() / 60
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

        trunc_function = self.GROUP_FUNCTIONS[group_by]

        trend_rows = (
            queryset
            .annotate(period_date=trunc_function("received_at"))
            .values("period_date")
            .annotate(
                resolved_count=Count(
                    "id",
                    filter=Q(
                        status__in=[
                            ConsultRequest.Status.RESOLVED,
                            ConsultRequest.Status.CLOSED,
                        ]
                    ),
                ),
            )
            .order_by("period_date")
        )

        trend = [
            {
                "date": row["period_date"].date(),
                "requestCount": row["request_count"],
                "resolvedCount": row["resolved_count"],
            }
            for row in trend_rows
        ]

        return success_response(
            {
                "period": {
                    "from": from_date,
                    "to": to_date,
                },
                "summary": {
                    "totalRequests": total_requests,
                    "criticalRequests": critical_requests,
                    "highRequests": high_requests,
                    "resolvedRequests": resolved_requests,
                    "averageResponseMinutes": average_response_minutes,
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

    def _validate_parameters(self, request):
        today = timezone.localdate()
        default_from = today - timedelta(days=30)

        from_value = request.query_params.get("from")
        to_value = request.query_params.get("to")
        group_by = request.query_params.get("groupBy", "DAY")

        from_date = parse_date(from_value) if from_value else default_from
        to_date = parse_date(to_value) if to_value else today

        if from_date is None or to_date is None:
            raise InvalidDashboardParameter(
                "날짜는 YYYY-MM-DD 형식이어야 합니다."
            )

        if from_date > to_date:
            raise InvalidDashboardParameter(
                "조회 시작일은 종료일보다 늦을 수 없습니다."
            )

        if group_by not in self.GROUP_FUNCTIONS:
            raise InvalidDashboardParameter(
                "groupBy는 DAY, WEEK, MONTH 중 하나여야 합니다."
            )

        return from_date, to_date, group_by