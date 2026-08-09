from datetime import date

from rest_framework import serializers
from .models import User


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )
    passwordConfirm = serializers.CharField(
        write_only=True,
    )

    birthDate = serializers.DateField(
        input_formats=["%Y%m%d"],
    )
    protectionEndDate = serializers.DateField()

    region = serializers.DictField()

    housingType = serializers.ChoiceField(
        choices=User.HousingType.choices,
    )
    incomeType = serializers.ChoiceField(
        choices=User.IncomeType.choices,
    )
    employmentType = serializers.ChoiceField(
        choices=User.EmploymentType.choices,
    )
    educationStatus = serializers.ChoiceField(
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

    def validate_email(self, value):    # 이메일 중복 확인
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "이미 가입된 이메일입니다."
            )
        return value

        
    def validate_username(self, value):     # 유저명 중복 확인
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "이미 사용 중인 아이디입니다."
            )
        return value

# 추가 기능: 비밀번호 유효성 검사
    # def validate_password(self, value):
    #     if len(value) < 8:
    #         raise serializers.ValidationError(
    #             "비밀번호는 8자 이상이어야 합니다."
    #         )

    #     if not any(char.isupper() for char in value):
    #         raise serializers.ValidationError(
    #             "비밀번호에 대문자가 포함되어야 합니다."
    #         )

    #     if not any(char.isdigit() for char in value):
    #         raise serializers.ValidationError(
    #             "비밀번호에 숫자가 포함되어야 합니다."
    #         )

    #     if not any(not char.isalnum() for char in value):
    #         raise serializers.ValidationError(
    #             "비밀번호에 특수문자가 포함되어야 합니다."
    #         )

    #     return value

    def validate(self, attrs):
        if attrs["password"] != attrs["passwordConfirm"]:
            raise serializers.ValidationError({
                "passwordConfirm": "비밀번호가 일치하지 않습니다."
            })

        if attrs["birthDate"] > date.today():
            raise serializers.ValidationError({
                "birthDate": "생년월일은 미래 날짜일 수 없습니다."
            })

        region = attrs["region"]

        if not region.get("sido"):
            raise serializers.ValidationError({
                "region": "sido는 필수입니다."
            })

        if not region.get("sigungu"):
            raise serializers.ValidationError({
                "region": "sigungu는 필수입니다."
            })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("passwordConfirm")

        birth_date = validated_data.pop("birthDate")
        protection_end_date = validated_data.pop("protectionEndDate")
        region = validated_data.pop("region")

        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            birthDate=birth_date,
            protectionEndDate=protection_end_date,
            sido=region["sido"],
            sigungu=region["sigungu"],
            detailAddress=region.get("detailAddress"),
            housingType=validated_data["housingType"],
            incomeType=validated_data["incomeType"],
            employmentType=validated_data["employmentType"],
            educationStatus=validated_data["educationStatus"],
        )

        user.set_password(password)
        user.save()

        return user

class EmailCheckSerializer(serializers.Serializer):     # 이메일 형식 확인
    email = serializers.EmailField()

class UsernameCheckSerializer(serializers.Serializer):  # 유저명 형식 확인
    username = serializers.CharField(max_length=30)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)