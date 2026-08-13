from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=150)
    license_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_membership",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.user.email}"


class ConsultRequest(models.Model):
    class UrgencyLevel(models.TextChoices):
        LOW = "LOW", "낮음"
        MEDIUM = "MEDIUM", "보통"
        HIGH = "HIGH", "높음"
        CRITICAL = "CRITICAL", "긴급"

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "접수"
        ASSIGNED = "ASSIGNED", "배정"
        IN_PROGRESS = "IN_PROGRESS", "상담 진행 중"
        RESOLVED = "RESOLVED", "해결"
        CLOSED = "CLOSED", "종료"

    class RiskType(models.TextChoices):
        HOUSING_FRAUD = "HOUSING_FRAUD", "주거 사기"
        FINANCIAL_SCAM = "FINANCIAL_SCAM", "금융 사기"
        LEGAL = "LEGAL", "법률"
        EMPLOYMENT = "EMPLOYMENT", "취업"
        WELFARE = "WELFARE", "복지"
        SAFETY = "SAFETY", "신변 안전"
        OTHER = "OTHER", "기타"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="consult_requests",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consult_requests",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_consult_requests",
        blank=True,
        null=True,
    )

    urgency_level = models.CharField(
        max_length=10,
        choices=UrgencyLevel.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    risk_type = models.CharField(
        max_length=30,
        choices=RiskType.choices,
        default=RiskType.OTHER,
    )

    summary = models.TextField()
    structured_report = models.JSONField(default=dict, blank=True)
    pre_interview = models.JSONField(default=list, blank=True)
    consent_scope = models.JSONField(default=list, blank=True)
    linkage_consented = models.BooleanField(default=False)

    received_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at", "-id"]
        indexes = [
            models.Index(
                fields=["organization", "status", "-received_at"]
            ),
            models.Index(
                fields=[
                    "organization",
                    "urgency_level",
                    "-received_at",
                ]
            ),
            models.Index(
                fields=["organization", "risk_type"]
            ),
        ]

    @property
    def user_alias(self):
        return f"청년_{self.requester_id:04d}"

    def __str__(self):
        return f"ConsultRequest(id={self.id}, status={self.status})"