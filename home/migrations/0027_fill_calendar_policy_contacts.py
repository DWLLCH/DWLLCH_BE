# -*- coding: utf-8 -*-
"""캘린더 유래 정책에 주관 기관과 신청 바로가기 링크를 채운다.

home/data 의 "자립준비청년_통합28건_상세데이터_바로가기 링크 첨부" 를 옮긴 것으로,
organization 이 "미정" 이고 consult_link 가 비어 있던 정책을 보완한다.

    공고/주관        -> organization
    신청바로가기 링크 -> consult_link

대상은 policy_id 가 없는 캘린더 유래 정책뿐이다.
기존 7건은 0017 에서 이미 기관과 상담 링크를 채워 두었으므로 덮어쓰지 않는다.

reverse 는 이전 상태(organization "미정", consult_link 없음)로 되돌린다.
"""

from django.db import migrations


PLACEHOLDER_ORGANIZATION = "미정"

POLICY_CONTACTS = [
    {
        "title": "자립정착금 지원사업",
        "organization": "전국 각 광역·기초 지자체 (시·군·구청)",
        "consult_link": "https://www.gov.kr",
    },
    {
        "title": "디딤씨앗통장(아동발달지원계좌) 매칭 지원",
        "organization": "보건복지부 / 아동권리보장원",
        "consult_link": "https://www.adongdream.or.kr",
    },
    {
        "title": "국민기초생활보장 청년소득공제 특례",
        "organization": "보건복지부 / 관할 행정복지센터",
        "consult_link": "https://www.bokjiro.go.kr",
    },
    {
        "title": "자립준비청년 SOS 긴급지원사업",
        "organization": "초록우산어린이재단 / 사회복지공동모금회",
        "consult_link": "https://www.childfund.or.kr",
    },
    {
        "title": "LH 공공임대주택 우선공급 제도",
        "organization": "한국토지주택공사(LH)",
        "consult_link": "https://apply.lh.or.kr",
    },
    {
        "title": "청년 전세임대주택 융자지원 사업",
        "organization": "주택도시기금 (HUG / LH)",
        "consult_link": "https://nhuf.molit.go.kr",
    },
    {
        "title": "지자체 청년 부동산 중개보수/이사비 지원",
        "organization": "서울시 청년몽땅정보통 및 각 지자체 청년포털",
        "consult_link": "https://youth.seoul.go.kr",
    },
    {
        "title": "자립준비청년 월세 한시 특별지원사업",
        "organization": "국토교통부 / 한국토지주택공사",
        "consult_link": "https://www.bokjiro.go.kr",
    },
    {
        "title": "국가장학금 자립준비청년 우선선발 지원",
        "organization": "한국장학재단",
        "consult_link": "https://www.kosaf.go.kr",
    },
    {
        "title": "취업 후 상환 학자금 생활비 대출 무이자 지원",
        "organization": "한국장학재단",
        "consult_link": "https://www.kosaf.go.kr",
    },
    {
        "title": "자립준비청년 대학생 생활지원 장학사업",
        "organization": "아동권리보장원 / 주요 장학재단",
        "consult_link": "https://jaripon.ncrc.or.kr",
    },
    {
        "title": "국민취업지원제도(자립준비청년 특례) 사업",
        "organization": "고용노동부",
        "consult_link": "https://www.kua.go.kr",
    },
    {
        "title": "자립준비청년 직업훈련비 및 면접비 지원",
        "organization": "고용노동부 HRD-Net / 지자체 청년포털",
        "consult_link": "https://www.hrd.go.kr",
    },
    {
        "title": "공공기관·기업 연계 맞춤형 일경험 인턴십",
        "organization": "고용노동부 청년일경험 통합지원센터",
        "consult_link": "https://www.work.go.kr/experi",
    },
    {
        "title": "전국민 마음투자 심리상담 바우처 지원",
        "organization": "보건복지부 / 관할 읍면동 행정복지센터",
        "consult_link": "https://www.bokjiro.go.kr",
    },
    {
        "title": "바람개비서포터즈 활동 지원사업",
        "organization": "아동권리보장원 자립정보ON",
        "consult_link": "https://jaripon.ncrc.or.kr",
    },
    {
        "title": "자립준비청년 문화·힐링 캠프 지원 프로그램",
        "organization": "한국청소년활동진흥원 / 시·도 자립지원전담기관",
        "consult_link": "https://jaripon.ncrc.or.kr",
    },
]


def fill_contacts(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for row in POLICY_CONTACTS:
        Policy.objects.filter(title=row["title"]).update(
            organization=row["organization"],
            consult_link=row["consult_link"],
        )


def restore_placeholder_contacts(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    titles = [row["title"] for row in POLICY_CONTACTS]
    Policy.objects.filter(title__in=titles).update(
        organization=PLACEHOLDER_ORGANIZATION,
        consult_link=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_fill_calendar_policy_details"),
    ]

    operations = [
        migrations.RunPython(fill_contacts, restore_placeholder_contacts),
    ]
