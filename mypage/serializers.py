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