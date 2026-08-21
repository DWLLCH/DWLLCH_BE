# -*- coding: utf-8 -*-
"""통장 쪼개기 표의 문구를 디자인 기준으로 교체한다.

0006 은 확보돼 있던 엑셀 원문을 기계적으로 세 컬럼으로 나눠 넣었다.
표 칸에 맞게 다시 쓴 디자인 문구가 최종 기준으로 확정되어 값만 교체한다.
구조(section/headers/rows)와 붙는 위치는 그대로다.
"""

from django.db import migrations


BRIEFING_TITLE = "자립 준비 중인 청년 필수 금융 치트키"
SECTION = "2. 텅장 방지! 통장 쪼개기 기술"
HEADERS = ["통장 종류", "활용 목적", "치트키(관리 팁)"]

DESIGN_ROWS = [
    [
        "수입 통장",
        "모든 수입이 들어오고 고정 지출이 나가는 통장",
        "자동이체 날짜를 모두 통일하기",
    ],
    [
        "생활금 통장",
        "식비, 쇼핑 등 통제할 수 있는 변동 지출 관리",
        "한 달 예산 맞춰 이체 해두기",
    ],
    [
        "비상금 통장",
        "병원비 등 예상 못한 지출 대비용",
        "이자 높은 파킹통장 이용하기",
    ],
]

SOURCE_ROWS = [
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
]


def _set_rows(apps, rows):
    Briefing = apps.get_model("briefing", "Briefing")

    briefing = Briefing.objects.filter(title=BRIEFING_TITLE).first()
    if briefing is None:
        return

    tables = briefing.content_tables or []
    updated = False

    for table in tables:
        if table.get("section") != SECTION:
            continue

        table["headers"] = HEADERS
        table["rows"] = [list(row) for row in rows]
        updated = True

    if not updated:
        return

    briefing.content_tables = tables
    briefing.save(update_fields=["content_tables"])


def apply_design_copy(apps, schema_editor):
    _set_rows(apps, DESIGN_ROWS)


def restore_source_copy(apps, schema_editor):
    _set_rows(apps, SOURCE_ROWS)


class Migration(migrations.Migration):

    dependencies = [
        ("briefing", "0006_extract_bank_split_table"),
    ]

    operations = [
        migrations.RunPython(apply_design_copy, restore_source_copy),
    ]
