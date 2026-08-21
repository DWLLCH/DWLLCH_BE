# -*- coding: utf-8 -*-
"""통장 쪼개기 섹션을 문단 텍스트에서 표 구조로 옮긴다.

"[수입통장]: 목적, 팁" 형태의 한 줄짜리 텍스트라 프론트가 쉼표/괄호 위치로
직접 파싱해야 했고, 문구가 조금만 바뀌어도 표가 깨졌다.
헤더와 행으로 나눠 content_tables 에 저장한다.

원문 줄은 content 에서 걷어낸다. 남겨두면 같은 내용이 문단과 표로
두 번 노출된다. 섹션 제목은 그대로 두고, 표가 어느 섹션에 붙는지는
content_tables 의 section 으로 알린다.
"""

from django.db import migrations


BRIEFING_TITLE = "자립 준비 중인 청년 필수 금융 치트키"
SECTION = "2. 텅장 방지! 통장 쪼개기 기술"
HEADING = "## " + SECTION

SOURCE_BODY = (
    "• [수입통장]: 모든 급여/지원금이 들어오는 메인 허브, "
    "자동이체 납부일을 급여일 직후로 통일\n"
    "• [생활비통장]: 식비/쇼핑/교통 등 변동지출용, "
    "한 달 예산만 체크카드 연결 계좌로 이체하여 사용\n"
    "• [비상금통장]: 최소 3개월 치 생활비 보관, "
    "수시 입출금 및 하루만 넣어도 이자가 붙는 고금리 파킹통장/CMA 활용"
)

TABLE = {
    "section": SECTION,
    "headers": ["통장 종류", "활용 목적", "치트키(관리 팁)"],
    "rows": [
        [
            "수입통장",
            "모든 급여/지원금이 들어오는 메인 허브",
            "자동이체 납부일을 급여일 직후로 통일",
        ],
        [
            "생활비통장",
            "식비/쇼핑/교통 등 변동지출용",
            "한 달 예산만 체크카드 연결 계좌로 이체하여 사용",
        ],
        [
            "비상금통장",
            "최소 3개월 치 생활비 보관",
            "수시 입출금 및 하루만 넣어도 이자가 붙는 고금리 파킹통장/CMA 활용",
        ],
    ],
}


def extract_table(apps, schema_editor):
    Briefing = apps.get_model("briefing", "Briefing")

    briefing = Briefing.objects.filter(title=BRIEFING_TITLE).first()
    if briefing is None:
        return

    briefing.content = briefing.content.replace(
        HEADING + "\n\n" + SOURCE_BODY, HEADING
    )
    briefing.content_tables = [TABLE]
    briefing.save(update_fields=["content", "content_tables"])


def restore_table_as_text(apps, schema_editor):
    Briefing = apps.get_model("briefing", "Briefing")

    briefing = Briefing.objects.filter(title=BRIEFING_TITLE).first()
    if briefing is None:
        return

    if SOURCE_BODY not in briefing.content:
        briefing.content = briefing.content.replace(
            HEADING, HEADING + "\n\n" + SOURCE_BODY
        )

    briefing.content_tables = []
    briefing.save(update_fields=["content", "content_tables"])


class Migration(migrations.Migration):

    dependencies = [
        ("briefing", "0005_briefing_content_tables_alter_briefing_content"),
    ]

    operations = [
        migrations.RunPython(extract_table, restore_table_as_text),
    ]
