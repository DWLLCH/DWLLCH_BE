# -*- coding: utf-8 -*-
"""정책DB 엑셀에서 온 정책 7건에 원본 policy_id 를 채운다.

0015~0017 은 Policy 에 policy_id 컬럼이 없어 title 로 매칭할 수밖에 없었다.
0018 에서 컬럼이 추가됐으므로 여기서 값을 채워, 앞으로 외부 데이터를 붙일 때
정책명이 바뀌어도 끊기지 않는 키로 쓸 수 있게 한다.

통합일정표에서 온 정책은 원본 ID 가 없어 policy_id 를 비워 둔다
(unique 이지만 null 은 중복이 허용된다).
"""

from django.db import migrations


# (policy_id, title)
POLICY_ID_BY_TITLE = [
    ("POL-CEN-001", "자립준비청년 자립수당 지급 (중앙부처)"),
    ("POL-LOC-CN01", "충남 자립준비청년 지원 (자립수당, 자립정착금, 대학생활안정자금)"),
    ("POL-LOC-CN02", "충남 자립지원 사업비 (맞춤형 자립지원통합서비스)"),
    ("POL-LOC-GB01", "경북 자립준비청년 자립수당지원"),
    ("POL-PRV-001", "LH 에너지 자립생활 안정자금 지원사업"),
    ("POL-PRV-002", "삼성 희망디딤돌 자립준비청년 취업지원사업"),
    ("INFO-BAS-001", "자립정보ON 및 자립준비청년 상담/멘토링 서비스"),
]


def fill_policy_id(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for policy_id, title in POLICY_ID_BY_TITLE:
        Policy.objects.filter(title=title).update(policy_id=policy_id)


def clear_policy_id(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    policy_ids = [policy_id for policy_id, _title in POLICY_ID_BY_TITLE]
    Policy.objects.filter(policy_id__in=policy_ids).update(policy_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0018_policy_policy_id"),
    ]

    operations = [
        migrations.RunPython(fill_policy_id, clear_policy_id),
    ]
