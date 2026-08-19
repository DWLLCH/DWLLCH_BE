from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

import hashlib
def validate_eligibility_items(value):
    if not isinstance(value, list):
        raise ValidationError(
            "eligibility_items는 배열이어야 합니다."
        )

    if not all(
        isinstance(item, str)
        for item in value
    ):
        raise ValidationError(
            "eligibility_items의 모든 항목은 문자열이어야 합니다."
        )


def validate_required_document_items(value):
    if not isinstance(value, list):
        raise ValidationError(
            "required_document_items는 배열이어야 합니다."
        )

    for item in value:
        if not isinstance(item, dict):
            raise ValidationError(
                "required_document_items의 각 항목은 객체여야 합니다."
            )

        label = item.get("label")
        issue_method = item.get("issueMethod")
        link_url = item.get("linkUrl")

        if not isinstance(label, str) or not label.strip():
            raise ValidationError(
                "제출서류의 label은 필수 문자열입니다."
            )

        if (
            issue_method is not None
            and not isinstance(issue_method, str)
        ):
            raise ValidationError(
                "issueMethod는 문자열 또는 null이어야 합니다."
            )

        if (
            link_url is not None
            and not isinstance(link_url, str)
        ):
            raise ValidationError(
                "linkUrl은 문자열 또는 null이어야 합니다."
            )


class ProtectionType(models.TextChoices):
    RESIDENTIAL_CARE = "RESIDENTIAL_CARE", "아동양육시설"
    GROUP_HOME = "GROUP_HOME", "공동생활가정"
    FOSTER_CARE = "FOSTER_CARE", "가정위탁"


class AgeRange(models.TextChoices):
    UNDER_18 = "UNDER_18", "만 18세 미만"
    AGE_18_24 = "AGE_18_24", "만 18세~24세"
    AGE_25_34 = "AGE_25_34", "만 25세~34세"


class IncomeCriteria(models.TextChoices):
    BASIC_LIVELIHOOD = "BASIC_LIVELIHOOD", "기초생활수급자"
    MEDIAN_INCOME = "MEDIAN_INCOME", "기준 중위소득"
    NEAR_POVERTY = "NEAR_POVERTY", "차상위계층"


def validate_choice_list(value, choices_cls, field_label):
    if not isinstance(value, list):
        raise ValidationError(
            f"{field_label}는 배열이어야 합니다."
        )

    valid_values = {choice.value for choice in choices_cls}

    invalid_values = [item for item in value if item not in valid_values]

    if invalid_values:
        raise ValidationError(
            f"{field_label}에 유효하지 않은 값이 있습니다: {', '.join(map(str, invalid_values))}"
        )


def validate_protection_types(value):
    validate_choice_list(value, ProtectionType, "protection_types")


def validate_age_ranges(value):
    validate_choice_list(value, AgeRange, "age_ranges")


def validate_income_criteria(value):
    validate_choice_list(value, IncomeCriteria, "income_criteria")


class Policy(models.Model):
    class Category(models.TextChoices):
        HOUSING = "HOUSING", "주거"
        EMPLOYMENT = "EMPLOYMENT", "취업"
        FINANCE = "FINANCE", "금융/자립수당"
        EDUCATION = "EDUCATION", "교육"
        MENTAL_HEALTH = "MENTAL_HEALTH", "심리/정서"
        ETC = "ETC", "기타"

    ProtectionType = ProtectionType
    AgeRange = AgeRange
    IncomeCriteria = IncomeCriteria

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300)
    content = models.TextField(help_text="이 지원사업은? (소개)")
    eligibility = models.TextField(help_text="내가 신청할 수 있나요? (신청 자격)")
    eligibility_items = models.JSONField(default=list, blank=True, validators=[validate_eligibility_items])
    required_document_items = models.JSONField(default=list, blank=True, validators=[validate_required_document_items,])
    application_method = models.TextField(help_text="언제까지 신청하나요? (신청 방법/기간)")
    required_documents = models.TextField(help_text="무엇을 준비해야 하나요? (준비 서류)")
    category = models.CharField(max_length=20, choices=Category.choices)
    protection_types = models.JSONField(default=list, blank=True, validators=[validate_protection_types], help_text="대상 보호유형 (복수 선택 가능)")
    age_ranges = models.JSONField(default=list, blank=True, validators=[validate_age_ranges], help_text="대상 연령 구간 (복수 선택 가능)")
    income_criteria = models.JSONField(default=list, blank=True, validators=[validate_income_criteria], help_text="대상 소득 기준 (복수 선택 가능)")
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="policy_scraps")
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name="scraps")
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