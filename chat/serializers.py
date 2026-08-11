from rest_framework import serializers

from chat.models import RiskCheckMessage, RiskCheckSession


class RiskCheckMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCheckMessage
        fields = [
            "id",
            "sender",
            "content",
            "risk_level",
            "analysis_result",
            "created_at",
        ]
        read_only_fields = ["risk_level", "analysis_result", "created_at"]

class RiskCheckSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCheckSession
        fields = [
            "id",
            "user",
            "status",
            "latest_risk_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "status", "latest_risk_level", "created_at", "updated_at"]

class RiskCheckSessionDetailSerializer(RiskCheckSessionSerializer):
    messages = RiskCheckMessageSerializer(many=True, read_only=True)

    class Meta(RiskCheckSessionSerializer.Meta):
        fields = RiskCheckSessionSerializer.Meta.fields + ["messages"]

class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField()