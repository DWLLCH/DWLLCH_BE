from urllib.parse import urlencode

from django.core import signing
from django.urls import reverse
from rest_framework import serializers

from chat.models import (
    RiskCheckMessage,
    RiskCheckMessageReport,
    RiskCheckSession,
    SupportConnection,
)


class RiskCheckMessageSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = RiskCheckMessage
        fields = [
            "id",
            "sender",
            "type",
            "content",
            "file_url",
            "risk_level",
            "analysis_result",
            "created_at",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None

        path = reverse(
            "chat:message-file",
            kwargs={"message_id": obj.id},
        )
        token = signing.dumps(
            {
                "message_id": obj.id,
                "user_id": obj.session.user_id,
            },
            salt="chat.risk-check.message-file",
        )
        signed_path = f"{path}?{urlencode({'token': token})}"

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(signed_path)

        return signed_path


class RiskCheckSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCheckSession
        fields = [
            "id",
            "user",
            "status",
            "latest_risk_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RiskCheckSessionDetailSerializer(RiskCheckSessionSerializer):
    messages = RiskCheckMessageSerializer(many=True, read_only=True)

    class Meta(RiskCheckSessionSerializer.Meta):
        fields = RiskCheckSessionSerializer.Meta.fields + ["messages"]


class MessageCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=RiskCheckMessage.MessageType.choices)
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
    )
    file = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        message_type = attrs["type"]
        content = attrs.get("content", "").strip()
        uploaded_file = attrs.get("file")

        if message_type == RiskCheckMessage.MessageType.TEXT and not content:
            raise serializers.ValidationError(
                {"content": "TEXT 메시지는 content가 필요합니다."}
            )

        if message_type == RiskCheckMessage.MessageType.TEXT and uploaded_file:
            raise serializers.ValidationError(
                {"file": "TEXT 메시지에는 이미지 파일을 첨부할 수 없습니다."}
            )

        if message_type == RiskCheckMessage.MessageType.IMAGE and not uploaded_file:
            raise serializers.ValidationError(
                {"file": "IMAGE 메시지는 이미지 파일이 필요합니다."}
            )

        if uploaded_file:
            allowed_types = {"image/jpeg", "image/png", "image/webp"}

            if uploaded_file.content_type not in allowed_types:
                raise serializers.ValidationError(
                    {"file": "JPEG, PNG, WEBP 이미지만 업로드할 수 있습니다."}
                )

            if uploaded_file.size > 10 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"file": "이미지는 최대 10MB까지 업로드할 수 있습니다."}
                )

        attrs["content"] = content
        return attrs


class MessageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCheckMessageReport
        fields = ["reason"]

    def validate_reason(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("신고 사유를 입력해주세요.")

        return value


class SupportConnectionSerializer(serializers.Serializer):
    consent = serializers.BooleanField(default=False)
    connectTo = serializers.ChoiceField(choices=SupportConnection.ConnectTo.choices)
