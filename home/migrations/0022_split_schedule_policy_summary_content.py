# -*- coding: utf-8 -*-
"""통합일정표에서 온 정책의 summary/content 를 서로 다른 문구로 분리한다.

0015 에서 두 필드를 모두 "모집 기간 + 준비 중" 한 문장으로 채워,
정책 상세의 "이 지원사업은?"(content) 과 "지원 내용"(summary) 칸에
사실상 같은 문장이 두 번 노출됐다.

- summary: "지원 내용" 요약. 언제 신청할 수 있는지를 한 줄로 안내한다.
- content: "이 지원사업은?" 소개. 어떤 정보가 등록돼 있고 무엇이 준비 중인지 설명한다.

모집 기간은 applicationStart/applicationEnd 로도 따로 내려가므로
content 에서는 반복하지 않는다.
"""

from django.db import migrations


SCHEDULE_ONLY_TITLES = [
    "자립정착금 지원사업",
    "디딤씨앗통장(아동발달지원계좌) 매칭 지원",
    "국민기초생활보장 청년소득공제 특례",
    "자립준비청년 SOS 긴급지원사업",
    "LH 공공임대주택 우선공급 제도",
    "청년 전세임대주택 융자지원 사업",
    "지자체 청년 부동산 중개보수/이사비 지원",
    "자립준비청년 월세 한시 특별지원사업",
    "국가장학금 자립준비청년 우선선발 지원",
    "취업 후 상환 학자금 생활비 대출 무이자 지원",
    "자립준비청년 대학생 생활지원 장학사업",
    "국민취업지원제도(자립준비청년 특례) 사업",
    "자립준비청년 직업훈련비 및 면접비 지원",
    "공공기관·기업 연계 맞춤형 일경험 인턴십",
    "전국민 마음투자 심리상담 바우처 지원",
    "바람개비서포터즈 활동 지원사업",
    "자립준비청년 문화·힐링 캠프 지원 프로그램",
]


def _period(policy):
    return "{:%Y-%m-%d} ~ {:%Y-%m-%d}".format(
        policy.application_start, policy.application_end
    )


def _new_summary(policy):
    return "{:%Y년 %m월 %d일}부터 {:%Y년 %m월 %d일}까지 신청할 수 있어요. 지원 금액과 세부 내용은 준비 중이에요.".format(
        policy.application_start, policy.application_end
    )


def _new_content(policy):
    return (
        "{} 모집 일정입니다.\n\n"
        "현재는 모집 기간만 확인된 상태로, 지원 대상과 지원 금액, "
        "제출 서류 등 자세한 내용은 아직 등록되지 않았습니다.\n"
        "신청 조건과 방법은 신청 기관 안내를 확인해 주시고, "
        "확인되는 대로 내용을 채워 넣을 예정입니다."
    ).format(policy.title)


def _old_summary(policy):
    return "모집 기간 {}. 상세 내용은 준비 중입니다.".format(_period(policy))


def _old_content(policy):
    return (
        "모집 기간: {}\n"
        "통합일정표에서 확보한 모집 일정만 등록된 정책입니다. "
        "상세 지원 내용은 추후 보완 예정입니다."
    ).format(_period(policy))


def _rewrite(apps, build_summary, build_content):
    Policy = apps.get_model("home", "Policy")

    for policy in Policy.objects.filter(title__in=SCHEDULE_ONLY_TITLES):
        if not (policy.application_start and policy.application_end):
            continue

        policy.summary = build_summary(policy)
        policy.content = build_content(policy)
        policy.save(update_fields=["summary", "content"])


def split_summary_and_content(apps, schema_editor):
    _rewrite(apps, _new_summary, _new_content)


def restore_shared_placeholder(apps, schema_editor):
    _rewrite(apps, _old_summary, _old_content)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0021_delete_stale_policy_match_cache"),
    ]

    operations = [
        migrations.RunPython(split_summary_and_content, restore_shared_placeholder),
    ]
