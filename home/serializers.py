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
    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "eligibility",
            "application_method",
            "required_documents",
            "category",
            "organization",
            "consult_phone",
            "consult_link",
            "application_start",
            "application_end",
            "created_at",
            "updated_at",
        ]

class HomeGuestSerializer(serializers.Serializer):
    banner_message = serializers.CharField()
    popular_policies = PolicyListSerializer(many=True)

class PolicyChatbotQuerySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    policy_id = serializers.IntegerField(required=False)


class PolicyChatbotResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()

class SimilarPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ["id", "title", "summary", "category", "organization"]