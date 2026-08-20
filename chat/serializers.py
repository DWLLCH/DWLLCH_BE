from urllib.parse import urlencode

from django.core import signing
from django.urls import reverse
from PIL import Image
from rest_framework import serializers

from chat.uploads import (
    DOCUMENT_CONTENT_TYPES,
    IMAGE_CONTENT_TYPES,
    MAX_UPLOAD_SIZE,
    has_expected_magic,
    read_head,
    resolve_content_type,
)

from chat.models import (
    RiskCheckMessage,
    RiskCheckMessageReport,
    RiskCheckSession,
    SupportConnection,
)


class RiskCheckMessageSerializer(serializers.ModelSerializer):
    fileUrl = serializers.SerializerMethodField()
    riskLevel = serializers.CharField(source="risk_level")
    analysisResult = serializers.JSONField(source="analysis_result")
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = RiskCheckMessage
        fields = [
            "id",
            "sender",
            "type",
            "content",
            "fileUrl",
            "riskLevel",
            "analysisResult",
            "createdAt",
        ]

    def get_fileUrl(self, obj):
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
    latestRiskLevel = serializers.CharField(source="latest_risk_level")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = RiskCheckSession
        fields = [
            "id",
            "user",
            "status",
            "latestRiskLevel",
            "createdAt",
            "updatedAt",
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
    # 이미지와 문서를 함께 받아야 해서 FileField 를 쓰고,
    # 이미지일 때의 실제 이미지 여부는 아래에서 직접 확인한다.
    file = serializers.FileField(required=False, allow_null=True)

    def validate(self, attrs):
        message_type = attrs["type"]
        content = attrs.get("content", "").strip()
        uploaded_file = attrs.get("file")

        if message_type == RiskCheckMessage.MessageType.TEXT:
            if not content:
                raise serializers.ValidationError(
                    {"content": "TEXT 메시지는 content가 필요합니다."}
                )

            if uploaded_file:
                raise serializers.ValidationError(
                    {"file": "TEXT 메시지에는 파일을 첨부할 수 없습니다."}
                )

        if message_type == RiskCheckMessage.MessageType.IMAGE and not uploaded_file:
            raise serializers.ValidationError(
                {"file": "IMAGE 메시지는 이미지 파일이 필요합니다."}
            )

        if message_type == RiskCheckMessage.MessageType.DOCUMENT and not uploaded_file:
            raise serializers.ValidationError(
                {"file": "DOCUMENT 메시지는 PDF 또는 DOCX 파일이 필요합니다."}
            )

        if uploaded_file:
            self._validate_upload(message_type, uploaded_file)

        attrs["content"] = content
        return attrs

    def _validate_upload(self, message_type, uploaded_file):
        content_type = resolve_content_type(uploaded_file)

        if message_type == RiskCheckMessage.MessageType.IMAGE:
            if content_type not in IMAGE_CONTENT_TYPES:
                raise serializers.ValidationError(
                    {"file": "JPEG, PNG, WEBP 이미지만 업로드할 수 있습니다."}
                )
        elif content_type not in DOCUMENT_CONTENT_TYPES:
            raise serializers.ValidationError(
                {"file": "PDF 또는 DOCX 파일만 업로드할 수 있습니다."}
            )

        if uploaded_file.size > MAX_UPLOAD_SIZE:
            limit_mb = MAX_UPLOAD_SIZE // (1024 * 1024)
            raise serializers.ValidationError(
                {"file": f"파일은 최대 {limit_mb}MB까지 업로드할 수 있습니다."}
            )

        if not has_expected_magic(content_type, read_head(uploaded_file)):
            raise serializers.ValidationError(
                {"file": "파일 내용이 확장자와 일치하지 않습니다."}
            )

        if message_type == RiskCheckMessage.MessageType.IMAGE:
            self._validate_real_image(uploaded_file)

    def _validate_real_image(self, uploaded_file):
        """확장자만 이미지인 파일을 걸러낸다. ImageField 가 하던 검증을 대신한다."""
        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image.verify()
        except Exception as exc:
            raise serializers.ValidationError(
                {"file": "이미지 파일을 읽을 수 없습니다."}
            ) from exc
        finally:
            uploaded_file.seek(0)


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
    connectTo = serializers.ChoiceField(
        choices=SupportConnection.ConnectTo.choices
    )