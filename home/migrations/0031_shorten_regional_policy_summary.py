# -*- coding: utf-8 -*-
"""통합28건에 대응 행이 없는 정책 4건의 summary 를 줄이고 다시 노출한다.

이 4건은 정책DB 엑셀에서 온 정책이라 통합28건 데이터셋에 애초에 없다.
새 문구를 지어내는 대신, 각 정책이 이미 가진 content/support_amount 에서
핵심만 남겨 통합28건과 같은 15자 이내 키워드형으로 줄인다.

    충남 자립준비청년 지원   : 자립수당 월 50만 / 정착금 1,000만 / 대학생활안정자금 200만
    충남 자립지원 사업비     : 월 40만 원 한도 맞춤형 지원 + 자조모임
    경북 자립준비청년 자립수당 : 월 50만 원, 5년간
    자립정보ON             : 선배 멘토링 + 정보 플랫폼 + 콜센터 상담

요약이 짧아져 카드에서 넘치지 않으므로 0030 에서 내렸던 노출을 되돌린다.
is_visible 필드는 남겨 둔다. 앞으로 정책을 임시로 내릴 때 쓴다.
"""

from django.db import migrations


# (title, 줄인 summary, 이전 summary)
POLICY_SUMMARIES = [
    (
        "충남 자립준비청년 지원 (자립수당, 자립정착금, 대학생활안정자금)",
        "수당·정착금·대학지원",
        "충남 거주 자립준비청년에게 자립수당, 정착금(1천만 원), 대학생활안정자금(200만 원) 지원",
    ),
    (
        "충남 자립지원 사업비 (맞춤형 자립지원통합서비스)",
        "맞춤형 자립 지원금",
        "자립기술평가를 통해 선정된 청년에게 월 40만 원 한도 내 맞춤형 지원 및 자조모임 지원",
    ),
    (
        "경북 자립준비청년 자립수당지원",
        "자립수당 (5년간)",
        "경북 거주 보호종료아동의 사회정착을 위해 매월 50만 원 자립수당 지급",
    ),
    (
        "자립정보ON 및 자립준비청년 상담/멘토링 서비스",
        "멘토링·정보·상담",
        "자립준비청년 선배의 멘토링 및 온라인 정보 플랫폼, 맞춤형 콜센터 상담",
    ),
]


def _apply(apps, summary_index, is_visible):
    Policy = apps.get_model("home", "Policy")

    for row in POLICY_SUMMARIES:
        Policy.objects.filter(title=row[0]).update(
            summary=row[summary_index],
            is_visible=is_visible,
        )


def shorten_and_show(apps, schema_editor):
    _apply(apps, 1, True)


def restore_and_hide(apps, schema_editor):
    _apply(apps, 2, False)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0030_hide_policies_without_short_summary"),
    ]

    operations = [
        migrations.RunPython(shorten_and_show, restore_and_hide),
    ]
