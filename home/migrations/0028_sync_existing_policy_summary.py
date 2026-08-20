# -*- coding: utf-8 -*-
"""정책DB 유래 정책의 summary 를 통합28건 데이터셋 기준으로 맞춘다.

summary 는 상세 화면의 "지원 내용" 칸과 목록 카드에 쓰이는 짧은 요약이다.
통합28건 데이터셋에서 카드 UI 줄바꿈을 막으려고 15자 이내 키워드형으로
표준화됐는데, 0026 은 캘린더 유래 정책만 갱신해 기존 정책은 40자 안팎의
긴 문장이 그대로 남아 있었다.

엑셀의 제도명이 우리 title 과 달라 자격/내용까지 대조해 같은 제도만 반영한다.

    LH 에너지 자립생활안정 지원사업 -> LH 에너지 자립생활 안정자금 지원사업
        (둘 다 LH 임대주택 거주 자립준비청년의 에너지 비용 지원)
    자립준비청년 자립수당지원      -> 자립준비청년 자립수당 지급 (중앙부처)
        (엑셀 자격이 "아동복지시설·가정위탁 보호종료 5년 이내"로 지역 제한이 없다.
         경북 자립수당은 경상북도 거주 한정이라 대상이 아니다.)
    삼성 희망디딤돌 ...           -> 제목이 정확히 같다

엑셀에 대응 행이 없는 충남 2건·경북 1건과, 같은 제도인지 확실하지 않은
자립정보ON 은 건드리지 않는다.

summary 만 바꾼다. content 는 우리 쪽이 더 상세해 유지한다.
"""

from django.db import migrations


# (title, 통합28건 기준 summary, 기존 summary)
POLICY_SUMMARIES = [
    (
        "자립준비청년 자립수당 지급 (중앙부처)",
        "자립수당 (최대 5년)",
        "자립준비청년의 안정적인 사회 정착을 위해 매월 50만 원의 자립수당 지급",
    ),
    (
        "LH 에너지 자립생활 안정자금 지원사업",
        "에너지·관리비 지원",
        "LH 임대주택 거주(예정) 자립준비청년에게 에너지 안정자금 40만 원 지원",
    ),
    (
        "삼성 희망디딤돌 자립준비청년 취업지원사업",
        "맞춤 직무교육·취업연계",
        "자립준비청년을 위한 직무교육, 기숙사 지원 및 월 100만 원 교육수당 지원",
    ),
]


def _apply(apps, index):
    Policy = apps.get_model("home", "Policy")

    for row in POLICY_SUMMARIES:
        Policy.objects.filter(title=row[0]).update(summary=row[index])


def sync_summaries(apps, schema_editor):
    _apply(apps, 1)


def restore_summaries(apps, schema_editor):
    _apply(apps, 2)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0027_fill_calendar_policy_contacts"),
    ]

    operations = [
        migrations.RunPython(sync_summaries, restore_summaries),
    ]
