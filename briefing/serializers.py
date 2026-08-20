from rest_framework import serializers

from .models import Briefing


class BriefingListSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(use_url=True, allow_null=True)

    class Meta:
        model = Briefing
        fields = ["id", "category", "title", "cardSummary", "thumbnail", "color", "icon"]

    cardSummary = serializers.CharField(source="card_summary")


class BriefingDetailSerializer(serializers.ModelSerializer):
    thumbnail = serializers.ImageField(use_url=True, allow_null=True)
    cardSummary = serializers.CharField(source="card_summary")
    keySummary = serializers.SerializerMethodField()
    contentTables = serializers.JSONField(source="content_tables")

    class Meta:
        model = Briefing
        fields = [
            "id",
            "category",
            "title",
            "cardSummary",
            "content",
            "contentTables",
            "thumbnail",
            "keySummary",
        ]

    def get_keySummary(self, obj):
        return self.context.get("key_summary_bullets", [])