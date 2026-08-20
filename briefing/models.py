import hashlib

from django.core.exceptions import ValidationError
from django.db import models


def validate_content_tables(value):
    """표형 콘텐츠 구조 검증.

    프론트가 문자열을 파싱하지 않고 바로 렌더링할 수 있어야 하므로,
    헤더와 행의 열 개수가 어긋나지 않는지까지 확인한다.
    """
    if not isinstance(value, list):
        raise ValidationError("content_tables는 배열이어야 합니다.")

    for table in value:
        if not isinstance(table, dict):
            raise ValidationError("content_tables의 각 항목은 객체여야 합니다.")

        section = table.get("section")
        headers = table.get("headers")
        rows = table.get("rows")

        if not isinstance(section, str) or not section.strip():
            raise ValidationError("표의 section은 필수 문자열입니다.")

        if not isinstance(headers, list) or not headers:
            raise ValidationError("표의 headers는 비어있지 않은 배열이어야 합니다.")

        if not all(isinstance(header, str) and header.strip() for header in headers):
            raise ValidationError("표의 headers 항목은 모두 문자열이어야 합니다.")

        if not isinstance(rows, list) or not rows:
            raise ValidationError("표의 rows는 비어있지 않은 배열이어야 합니다.")

        for row in rows:
            if not isinstance(row, list):
                raise ValidationError("표의 각 행은 배열이어야 합니다.")

            if not all(isinstance(cell, str) for cell in row):
                raise ValidationError("표의 셀 값은 모두 문자열이어야 합니다.")

            if len(row) != len(headers):
                raise ValidationError(
                    f"표의 행 길이({len(row)})가 headers 개수({len(headers)})와 다릅니다."
                )


class Briefing(models.Model):
    class Category(models.TextChoices):
        FINANCE = "FINANCE", "금융 & 경제"
        HOUSING = "HOUSING", "주거 & 일상자립"
        EMPLOYMENT = "EMPLOYMENT", "취업 & 진로"

    class Color(models.TextChoices):
        """프론트 카드 색상 박스. FE 디자인 토큰과 값이 일치해야 한다."""

        BLUE = "blue", "파랑"
        GREEN = "green", "초록"
        RED = "red", "빨강"

    class Icon(models.TextChoices):
        """프론트에 이미 존재하는 아이콘 에셋 목록."""

        CHART = "chart", "차트"
        CLOCK = "clock", "시계"
        COMPUTER = "computer", "컴퓨터"
        COURT = "court", "법원"
        DELIVERY = "delivery", "배송"
        DOCUMENT = "document", "문서"
        GRADUATION = "graduation", "학사모"
        GRAPH = "graph", "그래프"
        HEART = "heart", "하트"
        HOME = "home", "집"
        IDCARD = "idcard", "신분증"
        LETTER = "letter", "편지"
        MAGNIFIER = "magnifier", "돋보기"
        MONEY = "money", "돈"
        PHONE = "phone", "전화"
        PIGBANK = "pigbank", "돼지저금통"

    category = models.CharField(max_length=20, choices=Category.choices)
    color = models.CharField(
        max_length=10,
        choices=Color.choices,
        default=Color.BLUE,
        help_text="카드 색상 박스",
    )
    icon = models.CharField(
        max_length=20,
        choices=Icon.choices,
        default=Icon.DOCUMENT,
        help_text="카드 아이콘 (FE 아이콘 에셋 이름)",
    )
    title = models.CharField(max_length=200)
    card_summary = models.CharField(max_length=200, help_text="카드에 보이는 고정 짧은 설명")
    source_facts = models.JSONField(default=list, help_text="AI 요약의 재료가 되는 검증된 팩트 리스트")
    content = models.TextField(help_text="상세 본문(번호 섹션, Markdown). AI가 손대지 않음")
    content_tables = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_content_tables],
        help_text=(
            "표로 노출되는 콘텐츠. content 의 어느 섹션에 붙는지를 section 으로 지정한다. "
            '예: [{"section": "2. 통장 쪼개기", "headers": ["구분", "설명"], "rows": [["수입통장", "메인 허브"]]}]'
        ),
    )
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