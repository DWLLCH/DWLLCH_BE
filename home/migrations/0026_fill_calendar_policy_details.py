# -*- coding: utf-8 -*-
"""통합 상세 데이터셋으로 캘린더 유래 정책의 본문을 채운다.

home/data 의 "자립준비청년_통합28건_상세데이터_완성본" 을 옮긴 것으로,
모집 일정만 있어 안내 문구로 채워져 있던 정책에 실제 소개/요약/금액/자격을 넣는다.

    제도명    -> title (매칭 키)
    content  -> content   (1. 이 지원사업은?)
    summary  -> summary   (지원 내용 요약, 카드 UI 15자 표준)
    지원 금액 -> support_amount
    지원 자격 -> eligibility (2. 내가 신청할 수 있나요?)

대상은 policy_id 가 없는 캘린더 유래 정책뿐이다. 기존 7건은 이미 더 상세한
본문과 상담처 정보가 있어 덮어쓰지 않는다.

eligibility_items(자격요건 체크 항목)는 비워 둔다. 항목을 넣으면 상세 조회마다
항목 단위로 AI 판정이 돌아 호출량이 늘어나므로, 필요해지면 따로 채운다.

reverse 는 이전 안내 문구로 되돌린다.
"""

from django.db import migrations


NEWLINE = chr(10)

PLACEHOLDER_ELIGIBILITY = (
    "지원 대상 정보가 아직 등록되지 않았습니다. 신청 기관 안내를 확인해 주세요."
)

POLICY_DETAILS = [
    {
        "title": "자립정착금 지원사업",
        "content": "보호종료 초기 가전·가구 구입 및 생필품 마련 등 안정적인 일상 정착에 필요한 초기 비용을 지자체에서 일시금으로 지원합니다.",
        "summary": "정착금 일시 지원",
        "support_amount": "1,000만 원~2,000만 원 (지자체별 상이)",
        "eligibility": "만 18세 이후 만기 또는 연장 보호종료된 자립준비청년",
    },
    {
        "title": "디딤씨앗통장(아동발달지원계좌) 매칭 지원",
        "content": "아동이 매월 저축한 금액에 대해 정부가 1:2 매칭 적립금을 지원하여 만 18세 이후 학자금, 주거비 등 자립자금으로 활용하도록 돕습니다.",
        "summary": "정부 1:2 매칭 적립",
        "support_amount": "월 최대 10만 원 매칭",
        "eligibility": "보호대상아동 및 취약계층 아동 (적립금 사용: 보호종료 청년)",
    },
    {
        "title": "국민기초생활보장 청년소득공제 특례",
        "content": "자립준비청년이 일하여 소득이 발생하더라도 기초생활수급 자격 및 급여가 바로 탈락되지 않도록 소득공제 혜택을 부여합니다.",
        "summary": "근로소득 추가 공제",
        "support_amount": "소득 60만 원 공제 후 30% 추가 공제",
        "eligibility": "국민기초생활보장 수급 대상 자립준비청년 (만 24세 이하 등)",
    },
    {
        "title": "자립준비청년 SOS 긴급지원사업",
        "content": "갑작스러운 실직, 중증 질병, 주거 퇴거 등 긴급 위기 상황에 처한 자립준비청년에게 긴급 생계비와 의료비를 신속히 지원합니다.",
        "summary": "긴급 생계·의료비 지원",
        "support_amount": "항목별 실비 긴급 지급",
        "eligibility": "긴급 위기 상황에 처한 자립준비청년 (보호종료 5년 이내 우선)",
    },
    {
        "title": "LH 공공임대주택 우선공급 제도",
        "content": "주거 취약계층 청년의 주거 안정을 위해 한국토지주택공사(LH)의 국민임대, 행복주택 등 공공임대주택을 우선 배정하여 공급합니다.",
        "summary": "공공임대 우선 입주",
        "support_amount": "시세 대비 30~80% 수준",
        "eligibility": "보호종료 5년 이내 무주택 자립준비청년",
    },
    {
        "title": "청년 전세임대주택 융자지원 사업",
        "content": "입주 대상자가 거주할 주택을 직접 물색하면 LH가 주택 소유자와 전세계약을 체결한 후 저렴한 이자로 재임대하는 제도입니다.",
        "summary": "전세보증금 융자 지원",
        "support_amount": "최대 한도 내 보증금 지원",
        "eligibility": "보호종료 5년 이내 무주택 자립준비청년",
    },
    {
        "title": "지자체 청년 부동산 중개보수/이사비 지원",
        "content": "독립 생활을 시작하는 청년들의 경제적 부담을 덜어드리기 위해 부동산 중개수수료 및 이사 실비를 지자체에서 직접 지원합니다.",
        "summary": "중개보수·이사비 실비",
        "support_amount": "최대 40만 원 실비",
        "eligibility": "관할 지자체로 전입·이사 완료한 무주택 청년",
    },
    {
        "title": "자립준비청년 월세 한시 특별지원사업",
        "content": "고물가 및 주거비 상승으로 어려움을 겪는 청년들의 주거 안정을 위해 매월 정기적으로 월세를 분할 지원합니다.",
        "summary": "월세 한시 분할 지원",
        "support_amount": "월 최대 20만 원 (최대 12개월)",
        "eligibility": "보호종료 후 무주택 독립 거주 중인 자립준비청년",
    },
    {
        "title": "국가장학금 자립준비청년 우선선발 지원",
        "content": "고등교육 진학 청년의 학비 부담을 경감하기 위해 한국장학재단 국가장학금 소득분위 심사 시 우선 선발하여 등록금을 전액 지원합니다.",
        "summary": "등록금 전액 우선 장학",
        "support_amount": "등록금 전액 지원",
        "eligibility": "국내 대학에 재학 중인 보호종료 자립준비청년",
    },
    {
        "title": "취업 후 상환 학자금 생활비 대출 무이자 지원",
        "content": "학업 및 취업 준비 기간 동안 생활비 걱정 없이 학업에 전념할 수 있도록 취업 후 상환 생활비 대출의 발생 이자를 전액 면제합니다.",
        "summary": "생활비 대출 무이자",
        "support_amount": "대출이자 100% 면제",
        "eligibility": "취업 후 상환 학자금 생활비 대출 이용 자립준비청년",
    },
    {
        "title": "자립준비청년 대학생 생활지원 장학사업",
        "content": "대학 생활 중 생활비 부족으로 학업을 중단하지 않도록 학업 장려 및 생활 안정 목적의 장학금을 별도 지급합니다.",
        "summary": "생활비 장학금 지급",
        "support_amount": "학기별 100만~200만 원",
        "eligibility": "전문대 및 4년제 대학교에 재학 중인 자립준비청년",
    },
    {
        "title": "국민취업지원제도(자립준비청년 특례) 사업",
        "content": "취업을 준비하는 청년에게 1:1 맞춤 취업지원 서비스와 함께 매월 구직촉진수당을 지급하여 취업 성공을 밀착 지원합니다.",
        "summary": "맞춤취업+구직수당",
        "support_amount": "월 50만 원 (최대 6개월)",
        "eligibility": "취업을 희망하는 만 18세~34세 자립준비청년 (소득무관 참여 특례)",
    },
    {
        "title": "자립준비청년 직업훈련비 및 면접비 지원",
        "content": "구직 활동 경쟁력을 높이기 위해 전문 자격증 취득 훈련비 및 면접 준비에 소요되는 정장 대여비, 교통비 등을 실비 지원합니다.",
        "summary": "자격증·면접비 실비지원",
        "support_amount": "항목별 실비 지원",
        "eligibility": "구직 활동 및 역량 개발 중인 자립준비청년",
    },
    {
        "title": "공공기관·기업 연계 맞춤형 일경험 인턴십",
        "content": "실무 경험을 쌓고 취업 경쟁력을 강화할 수 있도록 주요 공공기관 및 우수 기업의 실전 일경험 인턴십 기회를 제공합니다.",
        "summary": "공공·민간 일경험 인턴",
        "support_amount": "참여 수당 지급 (급여형)",
        "eligibility": "직무 경험을 희망하는 미취업 자립준비청년",
    },
    {
        "title": "전국민 마음투자 심리상담 바우처 지원",
        "content": "심리적 고립감, 우울감, 진로 스트레스 등을 겪는 청년들에게 국가 공인 전문 심리상담 서비스를 바우처 형태로 전액 지원합니다.",
        "summary": "전문 심리상담 바우처",
        "support_amount": "총 8회기 상담 바우처",
        "eligibility": "심리·정서적 지원이 필요한 자립준비청년 및 일반 청년",
    },
    {
        "title": "바람개비서포터즈 활동 지원사업",
        "content": "자립에 성공한 선배 청년이 서포터즈가 되어 후배 자립준비청년에게 멘토링을 제공하고 권익 증진 활동에 참여하는 프로젝트입니다.",
        "summary": "선후배 멘토링·네트워크",
        "support_amount": "서포터즈 활동비 지급",
        "eligibility": "자립 역량을 갖추고 멘토링 활동을 희망하는 자립준비청년",
    },
    {
        "title": "자립준비청년 문화·힐링 캠프 지원 프로그램",
        "content": "또래 청년들과의 유대감을 쌓고 정서적 휴식을 취할 수 있도록 문화 예술 관람, 힐링 워크숍 및 1박 2일 캠프를 전액 무료로 운영합니다.",
        "summary": "문화체험·힐링캠프",
        "support_amount": "캠프·문화활동비 전액 무료",
        "eligibility": "정서 교류 및 문화 체험을 희망하는 자립준비청년",
    },
]


def fill_details(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for row in POLICY_DETAILS:
        Policy.objects.filter(title=row["title"]).update(
            content=row["content"],
            summary=row["summary"],
            support_amount=row["support_amount"],
            eligibility=row["eligibility"],
        )


def restore_placeholder(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    titles = [row["title"] for row in POLICY_DETAILS]

    for policy in Policy.objects.filter(title__in=titles):
        if not (policy.application_start and policy.application_end):
            continue

        policy.summary = (
            "{:%Y년 %m월 %d일}부터 {:%Y년 %m월 %d일}까지 신청할 수 있어요. "
            "지원 금액과 세부 내용은 준비 중이에요."
        ).format(policy.application_start, policy.application_end)
        policy.content = NEWLINE.join([
            "{} 모집 일정입니다.".format(policy.title),
            "",
            "현재는 모집 기간만 확인된 상태로, 지원 대상과 지원 금액, "
            "제출 서류 등 자세한 내용은 아직 등록되지 않았습니다.",
            "신청 조건과 방법은 신청 기관 안내를 확인해 주시고, "
            "확인되는 대로 내용을 채워 넣을 예정입니다.",
        ])
        policy.support_amount = None
        policy.eligibility = PLACEHOLDER_ELIGIBILITY
        policy.save(
            update_fields=["summary", "content", "support_amount", "eligibility"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0025_load_required_document_guide"),
    ]

    operations = [
        migrations.RunPython(fill_details, restore_placeholder),
    ]
