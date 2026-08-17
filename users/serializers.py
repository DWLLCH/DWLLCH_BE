from datetime import date

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegionSerializer(serializers.Serializer):
    sido = serializers.CharField(max_length=50)
    sigungu = serializers.CharField(max_length=50)
    detailAddress = serializers.CharField(
        source="detail_address",
        max_length=255,
        required=False,
        allow_blank=True,
    )


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )
    passwordConfirm = serializers.CharField(
        write_only=True,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "passwordConfirm",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "이미 가입된 이메일입니다."
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "이미 사용 중인 아이디입니다."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["passwordConfirm"]:
            raise serializers.ValidationError({
                "passwordConfirm": "비밀번호가 일치하지 않습니다."
            })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("passwordConfirm")

        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
        )

        user.set_password(password)
        user.save()

        return user


class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UsernameCheckSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ReissueSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()


class OnboardingProfileSerializer(serializers.ModelSerializer):
    region = RegionSerializer()

    birthDate = serializers.DateField(
        source="birth_date",
    )
    protectionType = serializers.ChoiceField(
        source="protection_type",
        choices=User.ProtectionType.choices,
    )
    protectionStatus = serializers.ChoiceField(
        source="protection_status",
        choices=User.ProtectionStatus.choices,
    )
    protectionEndDate = serializers.DateField(
        source="protection_end_date",
        required=False,
        allow_null=True,
    )
    housingType = serializers.ChoiceField(
        source="housing_type",
        choices=User.HousingType.choices,
    )
    housingSituation = serializers.ChoiceField(
        source="housing_situation",
        choices=User.HousingSituation.choices,
    )
    livingStatus = serializers.ListField(
        source="living_status",
        child=serializers.ChoiceField(
            choices=User.LivingStatus.choices,
        ),
    )
    incomeType = serializers.ChoiceField(
        source="income_type",
        choices=User.IncomeType.choices,
    )
    supportReceived = serializers.ListField(
        source="support_received",
        child=serializers.ChoiceField(
            choices=User.SupportType.choices,
        ),
    )
    neededHelp = serializers.ListField(
        source="needed_help",
        child=serializers.ChoiceField(
            choices=User.NeededHelp.choices,
        ),
    )
    profileCompleted = serializers.BooleanField(
        source="profile_completed",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "birthDate",
            "region",
            "protectionType",
            "protectionStatus",
            "protectionEndDate",
            "housingType",
            "housingSituation",
            "livingStatus",
            "incomeType",
            "supportReceived",
            "neededHelp",
            "profileCompleted",
        ]

    def validate_birthDate(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "생년월일은 미래 날짜일 수 없습니다."
            )

        return value

    def validate_neededHelp(self, value):
        if len(value) > 3:
            raise serializers.ValidationError(
                "최대 3개까지 선택할 수 있습니다."
            )

        return value

    def validate(self, attrs):
        protection_status = attrs.get("protection_status")
        protection_end_date = attrs.get("protection_end_date")

        if protection_status == User.ProtectionStatus.PROTECTED:
            attrs["protection_end_date"] = None

        elif protection_status in [
            User.ProtectionStatus.SCHEDULED,
            User.ProtectionStatus.ENDED,
        ]:
            if protection_end_date is None:
                raise serializers.ValidationError({
                    "protectionEndDate": "보호 종료일을 입력해주세요."
                })

        return attrs

    def update(self, instance, validated_data):
        region = validated_data.pop("region")

        instance.birth_date = validated_data["birth_date"]
        instance.sido = region["sido"]
        instance.sigungu = region["sigungu"]
        instance.detail_address = region.get("detail_address")

        instance.protection_type = validated_data["protection_type"]
        instance.protection_status = validated_data["protection_status"]
        instance.protection_end_date = validated_data.get(
            "protection_end_date"
        )

        instance.housing_type = validated_data["housing_type"]
        instance.housing_situation = validated_data["housing_situation"]
        instance.living_status = validated_data["living_status"]
        instance.income_type = validated_data["income_type"]
        instance.support_received = validated_data["support_received"]
        instance.needed_help = validated_data["needed_help"]

        instance.profile_completed = True

        instance.save()

        return instance


class PasswordChangeSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True)
    newPassword = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    def validate(self, attrs):
        if attrs["currentPassword"] == attrs["newPassword"]:
            raise serializers.ValidationError({
                "code": "COMMON_409_CONFLICT",
                "message": "현재 비밀번호와 새 비밀번호는 같을 수 없습니다.",
            })

        return attrs


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )


