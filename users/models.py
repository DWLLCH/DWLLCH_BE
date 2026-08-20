from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    birth_date = models.DateField(null=True, blank=True)
    protection_end_date = models.DateField(null=True, blank=True)

    sido = models.CharField(max_length=50, null=True, blank=True)
    sigungu = models.CharField(max_length=50, null=True, blank=True)
    detail_address = models.CharField(max_length=255, blank=True, null=True)

    class ProtectionType(models.TextChoices):
        RESIDENTIAL_CARE = "RESIDENTIAL_CARE", "아동양육시설"
        GROUP_HOME = "GROUP_HOME", "공동생활가정"
        FOSTER_CARE = "FOSTER_CARE", "가정위탁"
        ETC = "ETC", "기타"
        UNKNOWN = "UNKNOWN", "잘 모르겠어요"

    class ProtectionStatus(models.TextChoices):
        PROTECTED = "PROTECTED", "아직 보호 중이에요"
        SCHEDULED = "SCHEDULED", "보호 종료 예정이에요"
        ENDED = "ENDED", "보호 종료했어요"

    class HousingType(models.TextChoices):
        MONTHLY_RENT = "MONTHLY_RENT", "월세"
        JEONSE = "JEONSE", "전세"
        OWNED = "OWNED", "자가"
        FREE = "FREE", "무상 거주"
        FACILITY = "FACILITY", "시설·그룹홈 등"

    class HousingSituation(models.TextChoices):
        STABLE = "STABLE", "안정적으로 거주하고 있어요"
        MOVING = "MOVING", "이사할 집을 찾고 있어요"
        SEEKING_INDEPENDENCE = "SEEKING_INDEPENDENCE", "독립할 집을 찾고 있어요"
        BURDEN = "BURDEN", "주거비가 부담스러워요"
        PREPARING_END = "PREPARING_END", "곧 보호종료라 주거를 준비해야 해요"
        UNKNOWN = "UNKNOWN", "아직 잘 모르겠어요"

    class LivingStatus(models.TextChoices):
        SCHOOL = "SCHOOL", "학교에 다니고 있어요"
        EMPLOYED = "EMPLOYED", "직장에 다니고 있어요"
        PART_TIME = "PART_TIME", "아르바이트·파트타임으로 일하고 있어요"
        FREELANCE = "FREELANCE", "프리랜서·플랫폼 노동을 하고 있어요"
        SELF_EMPLOYED = "SELF_EMPLOYED", "자영업·창업을 하고 있어요"
        JOB_SEEKING = "JOB_SEEKING", "취업을 준비하고 있어요"
        NONE = "NONE", "현재 하고 있는 일이 없어요"

    class IncomeType(models.TextChoices):
        EARNED = "EARNED", "근로소득"
        BUSINESS = "BUSINESS", "사업소득"
        OTHER_ASSET = "OTHER_ASSET", "기타·재산소득"
        NONE = "NONE", "현재 소득이 없어요"

    class SupportType(models.TextChoices):
        SETTLEMENT_FUND = "SETTLEMENT_FUND", "자립정착금"
        EMPLOYMENT_SUPPORT = "EMPLOYMENT_SUPPORT", "취업 지원"
        INDEPENDENCE_ALLOWANCE = "INDEPENDENCE_ALLOWANCE", "자립수당"
        LIVING_SUPPORT = "LIVING_SUPPORT", "생활비 지원"
        HOUSING_SUPPORT = "HOUSING_SUPPORT", "주거지원"
        FINANCIAL_SUPPORT = "FINANCIAL_SUPPORT", "금융 지원"
        EDUCATION_SUPPORT = "EDUCATION_SUPPORT", "교육·장학 지원"
        ETC = "ETC", "기타"
        UNKNOWN = "UNKNOWN", "잘 모르겠어요"
        NONE = "NONE", "현재 받고 있는 지원이 없어요"

    class NeededHelp(models.TextChoices):
        HOUSING = "HOUSING", "주거"
        FINANCE = "FINANCE", "금융·생활비"
        EMPLOYMENT = "EMPLOYMENT", "취업·진로"
        EDUCATION = "EDUCATION", "교육"
        POLICY_INFO = "POLICY_INFO", "지원제도"
        ADMIN_DOCS = "ADMIN_DOCS", "행정·서류"
        COUNSELING = "COUNSELING", "상담·도움"

    protection_type = models.CharField(max_length=20, choices=ProtectionType.choices, null=True, blank=True)
    protection_status = models.CharField(max_length=20, choices=ProtectionStatus.choices, null=True, blank=True)
    housing_type = models.CharField(max_length=20, choices=HousingType.choices, null=True, blank=True)
    housing_situation = models.CharField(max_length=30, choices=HousingSituation.choices, null=True, blank=True)
    living_status = models.JSONField(default=list, blank=True)
    income_type = models.CharField(max_length=20, choices=IncomeType.choices, null=True, blank=True)
    support_received = models.JSONField(default=list, blank=True)
    needed_help = models.JSONField(default=list, blank=True)
    profile_completed = models.BooleanField(default=False)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "username"
    ]

    def __str__(self):
        return self.email


class UserBlock(models.Model):
    """한 사용자가 다른 사용자를 차단한 기록.

    브라우저 저장으로는 기기를 옮기면 목록이 사라져 계정 기준으로 보관한다.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocks",
        help_text="차단한 사용자",
    )
    target = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_by",
        help_text="차단당한 사용자",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target"],
                name="unique_user_block",
            ),
            # 자기 자신 차단은 뷰에서도 막지만, 데이터로도 남지 않게 한다.
            models.CheckConstraint(
                condition=~models.Q(user=models.F("target")),
                name="user_block_not_self",
            ),
        ]

    def __str__(self):
        return f"{self.user} blocked {self.target}"


class RefreshToken(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_token",
    )
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} refresh token"