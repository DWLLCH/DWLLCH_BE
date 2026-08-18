from django.conf import settings
from django.db import models

import hashlib

class Policy(models.Model):
    class Category(models.TextChoices):
        HOUSING = "HOUSING", "주거"
        EMPLOYMENT = "EMPLOYMENT", "취업"
        FINANCE = "FINANCE", "금융/자립수당"
        EDUCATION = "EDUCATION", "교육"
        MENTAL_HEALTH = "MENTAL_HEALTH", "심리/정서"
        ETC = "ETC", "기타"

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300)
    content = models.TextField(help_text="이 지원사업은? (소개)")
    eligibility = models.TextField(help_text="내가 신청할 수 있나요? (신청 자격)")
    application_method = models.TextField(help_text="언제까지 신청하나요? (신청 방법/기간)")
    required_documents = models.TextField(help_text="무엇을 준비해야 하나요? (준비 서류)")
    category = models.CharField(max_length=20, choices=Category.choices)
    target_condition = models.TextField(help_text="AI 큐레이션 매칭용 키워드 텍스트")
    organization = models.CharField(max_length=100, help_text="주관 기관")
    region_sido = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="특정 시도 대상 정책이면 입력, 전국 대상이면 비워둠",
    )
    consult_phone = models.CharField(max_length=20, blank=True, null=True, help_text="상담 전화번호")
    consult_link = models.URLField(blank=True, null=True, help_text="상담 신청/안내 링크")
    application_start = models.DateField(null=True, blank=True)
    application_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class PolicyScrap(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="policy_scraps",
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="scraps",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "policy"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} scrapped {self.policy}"

class CurationMatchCache(models.Model):
    profile_signature = models.CharField(max_length=16, db_index=True)
    policy_ids_hash = models.CharField(max_length=16)
    matched_result = models.JSONField(help_text="AI가 생성한 매칭 결과 (policy_id, match_reason 쌍의 리스트)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["profile_signature", "policy_ids_hash"]

    def __str__(self):
        return f"{self.profile_signature} - {self.policy_ids_hash}"


def compute_policy_ids_hash(policies):
    ids = sorted(p.id for p in policies)
    raw = ",".join(str(i) for i in ids)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]