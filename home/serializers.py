from rest_framework import serializers

from .models import Policy


class PolicyListSerializer(serializers.ModelSerializer):
    """목록 조회용 — 필요한 필드만 가볍게"""

    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "category",
            "organization",
            "application_end",
        ]


class PolicyDetailSerializer(serializers.ModelSerializer):
    """상세 조회용 — 전체 필드"""

    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "category",
            "target_condition",
            "organization",
            "application_start",
            "application_end",
            "created_at",
            "updated_at",
        ]