from rest_framework import serializers

from b2g.models import ConsultRequest


class ConsultRequestListSerializer(serializers.ModelSerializer):
    requestId = serializers.IntegerField(source="id", read_only=True)
    urgencyLevel = serializers.CharField(
        source="urgency_level",
        read_only=True,
    )
    riskType = serializers.CharField(source="risk_type", read_only=True)
    userAlias = serializers.SerializerMethodField()
    receivedAt = serializers.DateTimeField(
        source="received_at",
        read_only=True,
    )

    class Meta:
        model = ConsultRequest
        fields = [
            "requestId",
            "urgencyLevel",
            "status",
            "summary",
            "riskType",
            "userAlias",
            "receivedAt",
        ]

    def get_userAlias(self, obj):
        return f"청년_{obj.requester_id:04d}"


class ConsultRequestDetailSerializer(serializers.ModelSerializer):
    requestId = serializers.IntegerField(source="id", read_only=True)
    urgencyLevel = serializers.CharField(
        source="urgency_level",
        read_only=True,
    )
    riskType = serializers.CharField(source="risk_type", read_only=True)
    userAlias = serializers.SerializerMethodField()
    structuredReport = serializers.SerializerMethodField()
    preInterview = serializers.SerializerMethodField()
    consentScope = serializers.ListField(
        source="consent_scope",
        read_only=True,
    )
    receivedAt = serializers.DateTimeField(
        source="received_at",
        read_only=True,
    )

    class Meta:
        model = ConsultRequest
        fields = [
            "requestId",
            "urgencyLevel",
            "status",
            "riskType",
            "userAlias",
            "summary",
            "structuredReport",
            "preInterview",
            "consentScope",
            "receivedAt",
        ]

    def get_userAlias(self, obj):
        return f"청년_{obj.requester_id:04d}"

    def get_structuredReport(self, obj):
        if "STRUCTURED_REPORT" not in obj.consent_scope:
            return None

        return obj.structured_report

    def get_preInterview(self, obj):
        if "PRE_INTERVIEW" not in obj.consent_scope:
            return []

        return obj.pre_interview