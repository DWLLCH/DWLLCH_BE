from datetime import date
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Application, ChecklistItem, Notification

User = get_user_model()


class MypageStatusSerializer(serializers.Serializer):
    protection_end_date = serializers.DateField()
    d_day = serializers.IntegerField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "birth_date",
            "protection_end_date",
            "sido",
            "sigungu",
            "detail_address",
            "housing_type",
            "income_type",
            "employment_type",
            "education_status",
        ]

class ApplicationSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source="policy.title", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "policy",
            "policy_title",
            "status",
            "memo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["status"]