import hashlib

from django.db import models


class Briefing(models.Model):
    class Category(models.TextChoices):
        FINANCE = "FINANCE", "금융 & 경제"
        HOUSING = "HOUSING", "주거 & 일상자립"
        EMPLOYMENT = "EMPLOYMENT", "취업 & 진로"

    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=200)
    card_summary = models.CharField(max_length=200, help_text="카드에 보이는 고정 짧은 설명")
    source_facts = models.JSONField(default=list, help_text="AI 요약의 재료가 되는 검증된 팩트 리스트")
    content = models.TextField(help_text="상세 본문(번호 섹션+표 포함, Markdown). AI가 손대지 않음")
    thumbnail = models.ImageField(upload_to="briefings/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


def compute_profile_signature(user):
    raw = "|".join([
        ",".join(sorted(user.living_status or [])),
        ",".join(sorted(user.needed_help or [])),
        user.housing_situation or "",
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class BriefingSummaryCache(models.Model):
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name="summary_caches")
    profile_signature = models.CharField(max_length=16, db_index=True)
    generated_summary = models.JSONField(help_text="AI가 생성한 요약 (불릿 리스트)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["briefing", "profile_signature"]

    def __str__(self):
        return f"{self.briefing.title} - {self.profile_signature}"