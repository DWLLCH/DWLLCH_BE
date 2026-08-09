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

    region = RegionSerializer()

    birthDate = serializers.DateField(
        source="birth_date",
    )
    protectionEndDate = serializers.DateField(
        source="protection_end_date",
    )

    housingType = serializers.ChoiceField(
        source="housing_type",
        choices=User.HousingType.choices,
    )
    incomeType = serializers.ChoiceField(
        source="income_type",
        choices=User.IncomeType.choices,
    )
    employmentType = serializers.ChoiceField(
        source="employment_type",
        choices=User.EmploymentType.choices,
    )
    educationStatus = serializers.ChoiceField(
        source="education_status",
        choices=User.EducationStatus.choices,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "passwordConfirm",
            "birthDate",
            "region",
            "protectionEndDate",
            "housingType",
            "incomeType",
            "employmentType",
            "educationStatus",
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

        if attrs["birth_date"] > date.today():
            raise serializers.ValidationError({
                "birthDate": "생년월일은 미래 날짜일 수 없습니다."
            })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("passwordConfirm")

        region = validated_data.pop("region")

        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            birth_date=validated_data["birth_date"],
            protection_end_date=validated_data["protection_end_date"],
            sido=region["sido"],
            sigungu=region["sigungu"],
            detail_address=region.get("detail_address"),
            housing_type=validated_data["housing_type"],
            income_type=validated_data["income_type"],
            employment_type=validated_data["employment_type"],
            education_status=validated_data["education_status"],
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


class PasswordChangeSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True)
    newPassword = serializers.CharField(write_only=True)

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