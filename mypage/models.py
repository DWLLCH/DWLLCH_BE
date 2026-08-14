from django.conf import settings
from django.db import models

from home.models import Policy



class Application(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "신청 예정"
        IN_PROGRESS = "IN_PROGRESS", "신청 중"
        COMPLETED = "COMPLETED", "신청 완료"
        REJECTED = "REJECTED", "반려"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    memo = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.policy.title} ({self.status})"


class ChecklistItem(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )
    content = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.application} - {self.content}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=200)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.message}"

class ChecklistItem(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )
    content = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    issue_guide_text = models.CharField(max_length=200, blank=True, null=True, help_text="발급 안내 문구")
    issue_guide_url = models.URLField(blank=True, null=True, help_text="발급받기 버튼 연결 URL")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.application} - {self.content}"