from django.conf import settings
from django.db import models


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
    application_start = models.DateField(null=True, blank=True)
    application_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title