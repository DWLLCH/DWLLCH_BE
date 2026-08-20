from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Application, ChecklistItem, Notification

User = get_user_model()


class MypageStatusSerializer(serializers.Serializer):
    protectionEndDate = serializers.DateField(source="protection_end_date")
    dDay = serializers.IntegerField(source="d_day")


class RegionSerializer(serializers.Serializer):
    sido = serializers.CharField(max_length=50, required=False)
    sigungu = serializers.CharField(max_length=50, required=False)
    detailAddress = serializers.CharField(
        source="detail_address",
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class ProfileSerializer(serializers.ModelSerializer):
    birthDate = serializers.DateField(source="birth_date", read_only=True)
    region = RegionSerializer(source="*", required=False)
    protectionEndDate = serializers.DateField(source="protection_end_date", required=False, allow_null=True)
    protectionType = serializers.ChoiceField(
        source="protection_type", choices=User.ProtectionType.choices, required=False,
    )
    protectionStatus = serializers.ChoiceField(
        source="protection_status", choices=User.ProtectionStatus.choices, required=False,
    )
    housingType = serializers.ChoiceField(
        source="housing_type", choices=User.HousingType.choices, required=False,
    )
    housingSituation = serializers.ChoiceField(
        source="housing_situation", choices=User.HousingSituation.choices, required=False,
    )
    livingStatus = serializers.ListField(
        source="living_status",
        child=serializers.ChoiceField(choices=User.LivingStatus.choices),
        required=False,
    )
    incomeType = serializers.ChoiceField(
        source="income_type", choices=User.IncomeType.choices, required=False,
    )
    supportReceived = serializers.ListField(
        source="support_received",
        child=serializers.ChoiceField(choices=User.SupportType.choices),
        required=False,
    )
    neededHelp = serializers.ListField(
        source="needed_help",
        child=serializers.ChoiceField(choices=User.NeededHelp.choices),
        required=False,
    )
    profileCompleted = serializers.BooleanField(
        source="profile_completed",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "birthDate",
            "region",
            "protectionEndDate",
            "protectionType",
            "protectionStatus",
            "housingType",
            "housingSituation",
            "livingStatus",
            "incomeType",
            "supportReceived",
            "neededHelp",
            "profileCompleted",
        ]
        read_only_fields = ["email", "username"]


    def validate(self, attrs):
        protection_status = attrs.get(
            "protection_status",
            self.instance.protection_status,
        )
        protection_end_date = attrs.get(
            "protection_end_date",
            self.instance.protection_end_date,
        )

        if protection_status == User.ProtectionStatus.PROTECTED:
            attrs["protection_end_date"] = None

        elif (
            protection_status in [
                User.ProtectionStatus.SCHEDULED,
                User.ProtectionStatus.ENDED,
            ]
            and protection_end_date is None
        ):
            raise serializers.ValidationError({
                "protectionEndDate": "보호 종료일을 입력해주세요."
            })

        return attrs
    
    def validate_neededHelp(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("최대 3개까지 선택할 수 있습니다.")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    policyId = serializers.IntegerField(source="policy_id", read_only=True)
    policyTitle = serializers.CharField(source="policy.title", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "policy",
            "policyId",
            "policyTitle",
            "status",
            "memo",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = ["id", "createdAt", "updatedAt"]
        extra_kwargs = {"policy": {"write_only": True}}


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "status", "updatedAt"]
        read_only_fields = ["id", "updatedAt"]


class ChecklistItemSerializer(serializers.ModelSerializer):
    isDone = serializers.BooleanField(source="is_done")
    issueGuideText = serializers.CharField(source="issue_guide_text", allow_null=True, read_only=True)
    issueGuideUrl = serializers.URLField(source="issue_guide_url", allow_null=True, read_only=True)

    class Meta:
        model = ChecklistItem
        fields = ["id", "content", "isDone", "order", "issueGuideText", "issueGuideUrl"]
        read_only_fields = ["id", "content", "order"]


class NotificationSerializer(serializers.ModelSerializer):
    targetId = serializers.IntegerField(source="target_id", allow_null=True, read_only=True)
    isRead = serializers.BooleanField(source="is_read", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "message",
            "type",
            "targetId",
            "isRead",
            "createdAt",
        ]
        read_only_fields = ["type"]