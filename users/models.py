from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    # username = models.CharField(max_length=30, unique=True) abstractuser에서 이미 username 필드가 존재함

    birthDate = models.DateField()
    protectionEndDate = models.DateField()

    sido = models.CharField(max_length=50)
    sigungu = models.CharField(max_length=50)
    detailAddress = models.CharField(max_length=255, blank=True, null=True)

    class HousingType(models.TextChoices):
        MONTHLY_RENT = "MONTHLY_RENT", "월세"
        JEONSE = "JEONSE", "전세"
        OWNED = "OWNED", "자가"
        FREE = "FREE", "무상거주"

    class IncomeType(models.TextChoices):
        EARNED = "EARNED", "근로소득"
        BUSINESS = "BUSINESS", "사업소득"
        OTHER_ASSET = "OTHER_ASSET", "기타재산소득"
        NONE = "NONE", "소득없음"

    class EmploymentType(models.TextChoices):
        UNEMPLOYED = "UNEMPLOYED", "미취업"
        EMPLOYED = "EMPLOYED", "취업"
        PART_TIME = "PART_TIME", "아르바이트"
        SELF_EMPLOYED = "SELF_EMPLOYED", "자영업"

    class EducationStatus(models.TextChoices):
        ENROLLED = "ENROLLED", "재학"
        LEAVE_OF_ABSENCE = "LEAVE_OF_ABSENCE", "휴학"
        GRADUATED = "GRADUATED", "졸업"
        HIGH_SCHOOL_OR_BELOW = "HIGH_SCHOOL_OR_BELOW", "고등학교 이하"

    housingType = models.CharField(
        max_length=20,
        choices=HousingType.choices,
    )
    incomeType = models.CharField(
        max_length=20,
        choices=IncomeType.choices,
    )
    employmentType = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
    )
    educationStatus = models.CharField(
        max_length=30,
        choices=EducationStatus.choices,
    )

    USERNAME_FIELD = "email"
    
    REQUIRED_FIELDS = [
        # "username", 
        "birthDate",
        "protectionEndDate",
        "sido",
        "sigungu",
        "housingType",
        "incomeType",
        "employmentType",
        "educationStatus",
    ]

    def __str__(self):
        return self.email