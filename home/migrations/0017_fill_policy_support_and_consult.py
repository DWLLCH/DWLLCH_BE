# -*- coding: utf-8 -*-
"""정책DB 엑셀의 보완 표에서 지원 금액/상담처 정보를 채우는 데이터 마이그레이션.

엑셀 하단(헤더: policy_id, policy_name, supportAmount, consultPhone, consultLink)에
정책DB 7건에 대한 지원 금액과 상담 연락처가 추가되어 이를 반영한다.

- 헤더는 5개지만 실제 데이터는 6개 열이다.
  5번째 열은 상담처 설명 문구, 6번째 열이 실제 URL이라 consult_link 에는 6번째 열을 쓴다.
  (5번째 열 설명 문구는 저장할 필드가 없어 버린다.)
- 원본 URL 에 붙어 있던 추적 파라미터(utm_source 등)는 제거하고 저장한다.
- 이 마이그레이션 시점에는 Policy 에 policy_id 컬럼이 없어 매칭은 policy_name(title) 으로 한다.
  (policy_id 컬럼은 0018 에서 추가되고 0019 에서 채워진다.)
- 통합일정표에서 온 정책은 이 표의 대상이 아니며,
  매칭되는 정책이 없는 행은 조용히 건너뛴다.

reverse 는 이 마이그레이션이 채운 세 필드를 비운다.
support_amount 의 0015 시점 값까지 복원하지는 않는다.
"""

from django.db import migrations


# (policy_id, title, support_amount, consult_phone, consult_link)
CONSULT_ROWS = [
    (
        "POL-CEN-001",
        "자립준비청년 자립수당 지급 (중앙부처)",
        "매월 50만 원",
        "044-202-3431",
        "https://www.mohw.go.kr/menu.es?mid=a10711040900",
    ),
    (
        "POL-LOC-CN01",
        "충남 자립준비청년 지원 (자립수당, 자립정착금, 대학생활안정자금)",
        "자립수당 월 50만 원 / 자립정착금 1,000만 원 / 대학생활안정자금 200만 원",
        "041-635-2976",
        "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/644000000843",
    ),
    (
        "POL-LOC-CN02",
        "충남 자립지원 사업비 (맞춤형 자립지원통합서비스)",
        "월 40만 원 한도, 최대 500만 원 규모",
        "041-541-6553",
        "http://www.cnjarip.co.kr/main",
    ),
    (
        "POL-LOC-GB01",
        "경북 자립준비청년 자립수당지원",
        "월 50만 원, 5년간",
        "1522-0120",
        "https://www.kbjarip.or.kr/",
    ),
    (
        "POL-PRV-001",
        "LH 에너지 자립생활 안정자금 지원사업",
        "1인당 40만 원",
        "1600-1004",
        "https://apply.lh.or.kr/lhapply/main.do#gnrlPop",
    ),
    (
        "POL-PRV-002",
        "삼성 희망디딤돌 자립준비청년 취업지원사업",
        "교육수당 월 최대 100만 원 + 기숙사 숙식 지원",
        "02-330-0741",
        "https://csr.samsung.com/ko/program/samsung-stepping-stone-of-hope",
    ),
    (
        "INFO-BAS-001",
        "자립정보ON 및 자립준비청년 상담/멘토링 서비스",
        "금전 지원 없음",
        "1855-2455",
        "https://jaripon.ncrc.or.kr/home/kor/main.do",
    ),
]


def fill_support_and_consult(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for _policy_id, title, support_amount, consult_phone, consult_link in CONSULT_ROWS:
        Policy.objects.filter(title=title).update(
            support_amount=support_amount,
            consult_phone=consult_phone,
            consult_link=consult_link,
        )


def clear_support_and_consult(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    titles = [row[1] for row in CONSULT_ROWS]
    Policy.objects.filter(title__in=titles).update(
        support_amount=None,
        consult_phone=None,
        consult_link=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0016_alter_policy_eligibility_items_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_support_and_consult, clear_support_and_consult),
    ]
