import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from chat.uploads import CONTENT_TYPE_BY_SUFFIX


def risk_check_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in CONTENT_TYPE_BY_SUFFIX:
        suffix = ".bin"
    return f"chat/risk-check/{instance.session_id}/{uuid.uuid4().hex}{suffix}"


class RiskCheckSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "진행 중"
        STRUCTURED = "STRUCTURED", "상황 구조화 완료"
        CONNECTED = "CONNECTED", "조력자 연계 완료"
        CLOSED = "CLOSED", "종료"

    class RiskLevel(models.TextChoices):
        NONE = "NONE", "판독 전"
        LOW = "LOW", "낮음"
        MEDIUM = "MEDIUM", "보통"
        HIGH = "HIGH", "높음"
        CRITICAL = "CRITICAL", "긴급"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_check_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    latest_risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.NONE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RiskCheckSession(id={self.id}, user={self.user_id})"


class RiskCheckMessage(models.Model):
    class Sender(models.TextChoices):
        USER = "USER", "사용자"
        ASSISTANT = "ASSISTANT", "AI 챗봇"

    class MessageType(models.TextChoices):
        TEXT = "TEXT", "텍스트"
        IMAGE = "IMAGE", "이미지"
        DOCUMENT = "DOCUMENT", "문서(PDF/DOCX)"

    session = models.ForeignKey(
        RiskCheckSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(max_length=20, choices=Sender.choices)
    type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField(blank=True)
    file = models.FileField(
        upload_to=risk_check_upload_path,
        blank=True,
        null=True,
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskCheckSession.RiskLevel.choices,
        default=RiskCheckSession.RiskLevel.NONE,
    )
    analysis_result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"RiskCheckMessage(id={self.id}, sender={self.sender})"


class RiskCheckMessageReport(models.Model):
    message = models.ForeignKey(
        RiskCheckMessage,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_check_message_reports",
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_risk_message_report_per_user",
            )
        ]
        ordering = ["-created_at"]


class StructuredRiskReport(models.Model):
    session = models.OneToOneField(
        RiskCheckSession,
        on_delete=models.CASCADE,
        related_name="structured_report",
    )
    date = models.CharField(max_length=30, blank=True)
    amount = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    counterpart = models.CharField(max_length=255, blank=True)
    situation_summary = models.TextField(blank=True)
    risk_type = models.CharField(max_length=255, blank=True)
    risk_grade = models.CharField(
        max_length=20,
        choices=RiskCheckSession.RiskLevel.choices,
        default=RiskCheckSession.RiskLevel.NONE,
    )
    missing_fields = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SupportConnection(models.Model):
    class ConnectTo(models.TextChoices):
        SUPPORT_STAFF = "SUPPORT_STAFF", "조력자"
        COUNSELOR = "COUNSELOR", "상담사"
        EMERGENCY = "EMERGENCY", "긴급 지원"

    session = models.OneToOneField(
        RiskCheckSession,
        on_delete=models.CASCADE,
        related_name="support_connection",
    )
    connect_to = models.CharField(max_length=30, choices=ConnectTo.choices)
    consent = models.BooleanField(default=False)
    forced_connection = models.BooleanField(default=False)
    notice = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(consent=True)
                    | models.Q(forced_connection=True)
                ),
                name="support_connection_requires_consent_or_force",
            )
        ]
