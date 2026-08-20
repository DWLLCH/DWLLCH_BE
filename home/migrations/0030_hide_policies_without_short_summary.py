# -*- coding: utf-8 -*-
"""짧은 요약 문구를 확보하지 못한 정책 4건을 화면에서 내린다.

통합28건 데이터셋에 대응 행이 없어 카드용 15자 요약을 만들 근거가 없는
정책들이다. 40~52자 요약이 카드에서 여러 줄로 넘쳐 노출을 끈다.

삭제가 아니라 is_visible 플래그만 내린다.
상담 전화·신청 링크·제출서류 데이터가 붙어 있고, 지역 사용자에게는 필요한
정보라 문구가 확보되면 플래그만 다시 켜서 그대로 되살릴 수 있다.
"""

from django.db import migrations


HIDDEN_POLICY_TITLES = [
    "충남 자립준비청년 지원 (자립수당, 자립정착금, 대학생활안정자금)",
    "충남 자립지원 사업비 (맞춤형 자립지원통합서비스)",
    "경북 자립준비청년 자립수당지원",
    "자립정보ON 및 자립준비청년 상담/멘토링 서비스",
]


def hide_policies(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")
    Policy.objects.filter(title__in=HIDDEN_POLICY_TITLES).update(is_visible=False)


def show_policies(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")
    Policy.objects.filter(title__in=HIDDEN_POLICY_TITLES).update(is_visible=True)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0029_policy_is_visible"),
    ]

    operations = [
        migrations.RunPython(hide_policies, show_policies),
    ]
