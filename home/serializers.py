from rest_framework import serializers

from .models import Policy, PolicyScrap
from .services import judge_eligibility_item, GeminiRequestError
from briefing.models import compute_profile_signature

from .models import Policy, PolicyScrap, EligibilityJudgeCache

class PolicyListSerializer(serializers.ModelSerializer):
    applicationEnd = serializers.DateField(source="application_end")
    regionSido = serializers.CharField(source="region_sido", allow_null=True)
    updatedAt = serializers.DateTimeField(source="updated_at")
    supportAmount = serializers.CharField(source="support_amount", allow_null=True)
    matchLevel = serializers.SerializerMethodField()
    matchReason = serializers.SerializerMethodField()
    scrapCount = serializers.SerializerMethodField()

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
            "updatedAt",
            "supportAmount",
            "matchLevel",
            "matchReason",
            "scrapCount",
        ]

    def get_matchLevel(self, obj):
        match_map = self.context.get("match_map", {})
        match = match_map.get(obj.id)
        return match["match_level"] if match else None

    def get_matchReason(self, obj):
        match_map = self.context.get("match_map", {})
        match = match_map.get(obj.id)
        return match["match_reason"] if match else None

    def get_scrapCount(self, obj):
        if hasattr(obj, "scrap_count"):
            return obj.scrap_count
        return obj.scraps.count()


class RequiredDocumentSerializer(serializers.Serializer):
    label = serializers.CharField()
    issueMethod = serializers.CharField(allow_null=True)
    linkUrl = serializers.URLField(allow_null=True)


class EligibilityItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    met = serializers.CharField(allow_null=True)  # "MET" | "NEED_CHECK" | None(비로그인)


class PolicyDetailSerializer(serializers.ModelSerializer):
    applicationMethod = serializers.CharField(source="application_method")
    eligibility = serializers.SerializerMethodField()
    requiredDocuments = RequiredDocumentSerializer(source="required_document_items", many=True, read_only=True)
    consultPhone = serializers.CharField(source="consult_phone", allow_null=True)
    consultLink = serializers.URLField(source="consult_link", allow_null=True)
    regionSido = serializers.CharField(source="region_sido", allow_null=True)
    applicationStart = serializers.DateField(source="application_start", allow_null=True)
    applicationEnd = serializers.DateField(source="application_end", allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    supportAmount = serializers.CharField(source="support_amount", allow_null=True)
    matchLevel = serializers.SerializerMethodField()
    matchReason = serializers.SerializerMethodField()

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
            "supportAmount",
            "matchLevel",
            "matchReason",
        ]
    def get_matchLevel(self, obj):
        match_map = self.context.get("match_map", {})
        match = match_map.get(obj.id)
        return match["match_level"] if match else None

    def get_matchReason(self, obj):
        match_map = self.context.get("match_map", {})
        match = match_map.get(obj.id)
        return match["match_reason"] if match else None

    def get_eligibility(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        is_authenticated = bool(user and user.is_authenticated)

        items = []
        profile_signature = compute_profile_signature(user) if is_authenticated else None

        for label in obj.eligibility_items:
            entry = {"label": label, "met": None}

            if is_authenticated:
                cache = EligibilityJudgeCache.objects.filter(
                    policy=obj, eligibility_label=label, profile_signature=profile_signature
                ).first()

                if cache:
                    entry["met"] = cache.status
                else:
                    try:
                        status = judge_eligibility_item(label, user)
                    except GeminiRequestError:
                        status = "NEED_CHECK"

                    EligibilityJudgeCache.objects.update_or_create(
                        policy=obj, eligibility_label=label, profile_signature=profile_signature,
                        defaults={"status": status},
                    )
                    entry["met"] = status

            items.append(entry)
        return items


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
    policyId = serializers.IntegerField(source="policy_id", required=False)


class PolicyScrapSerializer(serializers.ModelSerializer):
    policyId = serializers.IntegerField(source="policy.id", read_only=True)
    policyTitle = serializers.CharField(source="policy.title", read_only=True)
    category = serializers.CharField(source="policy.category", read_only=True)
    applicationEnd = serializers.DateField(source="policy.application_end", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = PolicyScrap
        fields = [
            "id",
            "policyId",
            "policyTitle",
            "category",
            "applicationEnd",
            "createdAt",
        ]