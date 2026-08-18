from rest_framework import serializers

from .models import Policy


class PolicyListSerializer(serializers.ModelSerializer):
    applicationEnd = serializers.DateField(source="application_end")
    regionSido = serializers.CharField(
        source="region_sido",
        allow_null=True,
    )
    matchLevel = serializers.SerializerMethodField()
    matchReason = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "category",
            "organization",
            "regionSido",
            "applicationEnd",
            "matchLevel",
            "matchReason",
        ]

    def get_matchLevel(self, obj):
        match_map = self.context.get(
            "match_map",
            {},
        )

        match = match_map.get(obj.id)

        if not match:
            return None

        return match.match_level

    def get_matchReason(self, obj):
        match_map = self.context.get(
            "match_map",
            {},
        )

        match = match_map.get(obj.id)

        if not match:
            return None

        return match.match_reason


class PolicyDetailSerializer(serializers.ModelSerializer):
    applicationMethod = serializers.CharField(source="application_method")
    requiredDocuments = serializers.CharField(source="required_documents")
    consultPhone = serializers.CharField(
        source="consult_phone",
        allow_null=True,
    )
    consultLink = serializers.URLField(
        source="consult_link",
        allow_null=True,
    )
    regionSido = serializers.CharField(
        source="region_sido",
        allow_null=True,
    )
    applicationStart = serializers.DateField(
        source="application_start",
        allow_null=True,
    )
    applicationEnd = serializers.DateField(
        source="application_end",
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "eligibility",
            "applicationMethod",
            "requiredDocuments",
            "category",
            "organization",
            "regionSido",
            "consultPhone",
            "consultLink",
            "applicationStart",
            "applicationEnd",
            "createdAt",
            "updatedAt",
        ]


class SimilarPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            "id",
            "title",
            "summary",
            "category",
            "organization",
        ]


class PolicyChatbotQuerySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    policyId = serializers.IntegerField(
        source="policy_id",
        required=False,
    )