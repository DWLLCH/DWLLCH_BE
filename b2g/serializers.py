from rest_framework import serializers

from b2g.models import ConsultRequest


class ConsultRequestListSerializer(serializers.ModelSerializer):
    requestId = serializers.IntegerField(source="id")
    urgencyLevel = serializers.CharField(source="urgency_level")
    riskType = serializers.CharField(source="risk_type")
    userAlias = serializers.CharField(source="user_alias")
    receivedAt = serializers.DateTimeField(source="received_at")

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
    return obj.user_alias

class ConsultRequestDetailSerializer(serializers.ModelSerializer):
    requestId = serializers.IntegerField(source="id")
    urgencyLevel = serializers.CharField(source="urgency_level")
    riskType = serializers.CharField(source="risk_type")
    userAlias = serializers.CharField(source="user_alias")
    structuredReport = serializers.SerializerMethodField()
    preInterview = serializers.SerializerMethodField()
    consentScope = serializers.JSONField(source="consent_scope")
    receivedAt = serializers.DateTimeField(source="received_at")

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
        
    def get_structuredReport(self, obj):
        if "STRUCTURED_REPORT" not in obj.consent_scope:
            return None
        
        return obj.structured_report

    def get_preInterview(self, obj):
        if "PRE_INTERVIEW" not in obj.consent_scope:
            return []
        
        return obj.pre_interview