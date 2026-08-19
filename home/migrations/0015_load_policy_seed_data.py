# -*- coding: utf-8 -*-
"""home/data 의 엑셀 2종을 Policy 로 적재하는 데이터 마이그레이션.

- 자립준비청년_정책DB_형식.xlsx        -> 상세 정보까지 있는 정책 7건
- 자립준비청년_지원제도_통합일정표.xlsx -> 모집 일정만 있는 정책 17건
  ("자립수당 지급 사업"은 정책DB의 중앙부처 자립수당과 동일 제도라 중복 등록하지 않음)

엑셀을 마이그레이션 실행 시점에 읽지 않고 파싱 결과를 그대로 박아둔다.
(openpyxl 런타임 의존성을 만들지 않기 위함이며, 값 리뷰도 쉬워진다.)

protection_types / age_ranges / income_criteria 는 "지원 대상" 문구가
명시적으로 대상을 제한할 때만 채우고, 제한이 없거나 판단이 애매하면 빈 배열로 둔다.
"""

from datetime import date

from django.db import migrations


DOC_PLACEHOLDER = "제출 서류는 신청 기관 안내를 확인해 주세요."


# ---------------------------------------------------------------------------
# 1) 정책DB 엑셀 (상세 정보 보유)
# ---------------------------------------------------------------------------
DETAILED_POLICIES = [
    {
        "title": "자립준비청년 자립수당 지급 (중앙부처)",
        "summary": "자립준비청년의 안정적인 사회 정착을 위해 매월 50만 원의 자립수당 지급",
        "content": (
            "자립수당 결정 대상자 명의 계좌로 매월 50만 원을 지급합니다.\n"
            "[지원 기준]\n"
            "- 만 18세 이후 만기 또는 연장 보호종료된 자\n"
            "- 만 15세 이후 보호조치가 조기 종료된 자로서 만 18세가 된 때로부터 5년 이내인 자\n"
            "[처리 절차]\n"
            "초기상담 및 신청 -> 대상자 통합조사/심사 -> 확정/지원 -> 사후관리"
        ),
        "eligibility": (
            "아동복지시설, 가정위탁 보호종료 5년 이내 자립준비청년 "
            "(만 18세 이후 만기/연장 종료 또는 만 15세 이후 조기 종료 후 5년 이내, "
            "과거 2년 이상 연속 보호 필요)"
        ),
        "eligibility_items": [
            "아동복지시설 또는 가정위탁 보호가 종료된 자립준비청년",
            "만 18세 이후 만기/연장 보호종료 또는 만 15세 이후 조기 종료",
            "보호종료 후 5년 이내",
            "과거 2년 이상 연속 보호를 받은 이력",
        ],
        "application_method": "방문(읍면동 행정복지센터), 온라인(복지로), 우편/팩스",
        "required_documents": DOC_PLACEHOLDER,
        "category": "FINANCE",
        "protection_types": ["RESIDENTIAL_CARE", "FOSTER_CARE"],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "자립수당 현금지원 보호종료 5년 이내 아동복지시설 가정위탁 매월 50만원 생활비",
        "organization": "보건복지부",
        "region_sido": None,
        "support_amount": "월 50만원",
        # 정책DB 엑셀의 신청 기간이 "상시"이므로 기간을 비워 둔다.
        # 통합일정표의 "자립수당 지급 사업"이 같은 제도라 중복 등록만 하지 않고,
        # 일정표 쪽 모집 기간은 반영하지 않는다.
        "application_start": None,
        "application_end": None,
    },
    {
        "title": "충남 자립준비청년 지원 (자립수당, 자립정착금, 대학생활안정자금)",
        "summary": "충남 거주 자립준비청년에게 자립수당, 정착금(1천만 원), 대학생활안정자금(200만 원) 지원",
        "content": (
            "충남 지역 자립준비청년 초기비용 지원 (최대 920만 원 규모)\n"
            "- 자립수당: 1인 월 50만 원, 최대 60개월\n"
            "- 자립정착금: 1인 1,000만 원 일시 지원\n"
            "- 대학생활안정자금: 1인 200만 원 일시 지원"
        ),
        "eligibility": (
            "충청남도 내 거주하는 자립준비청년 "
            "(연령/혼인/소득 제한 없음, 대학생활안정자금은 대학진학자 한정)"
        ),
        "eligibility_items": [
            "충청남도 내 거주하는 자립준비청년",
            "연령/혼인/소득 제한 없음",
            "대학생활안정자금은 대학 진학자에 한정",
        ],
        "application_method": "관할 읍면동 행정복지센터 방문",
        "required_documents": DOC_PLACEHOLDER,
        "category": "FINANCE",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "충청남도 충남 거주 자립수당 자립정착금 대학생활안정자금 초기비용 대학진학",
        "organization": "충청남도",
        "region_sido": "충청남도",
        "support_amount": "최대 920만원 규모 (자립수당 월 50만원 / 정착금 1,000만원 / 대학생활안정자금 200만원)",
        "application_start": date(2026, 1, 1),
        "application_end": date(2026, 12, 31),
    },
    {
        "title": "충남 자립지원 사업비 (맞춤형 자립지원통합서비스)",
        "summary": "자립기술평가를 통해 선정된 청년에게 월 40만 원 한도 내 맞춤형 지원 및 자조모임 지원",
        "content": (
            "기본 사후관리 및 맞춤형 서비스 제공 (최대 500만 원 규모)\n"
            "- 자립지원통합서비스: 지표 평가 후 생활/주거/교육/취업 등 월 40만 원 한도 지원\n"
            "- 자조모임 지원: 바람개비 서포터즈 운영 지원"
        ),
        "eligibility": "충청남도 내 거주하는 보호 종료 5년 이내 자립준비청년",
        "eligibility_items": [
            "충청남도 내 거주하는 자립준비청년",
            "보호 종료 5년 이내",
        ],
        "application_method": "관할 읍면동 행정복지센터 방문",
        "required_documents": DOC_PLACEHOLDER,
        "category": "HOUSING",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "충청남도 충남 맞춤형 자립지원통합서비스 자립기술평가 생활 주거 교육 취업 자조모임 바람개비",
        "organization": "충청남도",
        "region_sido": "충청남도",
        "support_amount": "월 40만원 한도 (최대 500만원 규모)",
        "application_start": date(2026, 1, 1),
        "application_end": date(2026, 12, 1),
    },
    {
        "title": "경북 자립준비청년 자립수당지원",
        "summary": "경북 거주 보호종료아동의 사회정착을 위해 매월 50만 원 자립수당 지급",
        "content": (
            "보호대상아동 자립준비 역량 강화 지원\n"
            "- 지원 내용: 매월 50만 원 지급\n"
            "- 조건: 과거 2년 이상 연속 보호를 받은 자 중 만 18세 이후 보호종료 후 5년 이내인 자 등"
        ),
        "eligibility": "경상북도 내 거주하는 보호대상아동 (보호종료 5년 이내 등)",
        "eligibility_items": [
            "경상북도 내 거주하는 보호대상아동 또는 자립준비청년",
            "과거 2년 이상 연속 보호를 받은 이력",
            "만 18세 이후 보호종료 후 5년 이내",
        ],
        "application_method": "관할 시/군 주민센터",
        "required_documents": DOC_PLACEHOLDER,
        "category": "FINANCE",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "경상북도 경북 거주 자립수당 보호종료아동 매월 50만원 사회정착",
        "organization": "경상북도",
        "region_sido": "경상북도",
        "support_amount": "월 50만원",
        "application_start": date(2026, 1, 1),
        "application_end": date(2026, 12, 31),
    },
    {
        "title": "LH 에너지 자립생활 안정자금 지원사업",
        "summary": "LH 임대주택 거주(예정) 자립준비청년에게 에너지 안정자금 40만 원 지원",
        "content": (
            "자립준비청년의 주거 및 생활 안정을 위한 에너지 비용 지원\n"
            "- 1인당 총 40만 원의 에너지 자립생활 안정자금 지원"
        ),
        "eligibility": "LH 임대주택에 입주 거주 중이거나 입주 예정인 자립준비청년",
        "eligibility_items": [
            "LH 임대주택에 거주 중이거나 입주 예정인 자립준비청년",
        ],
        "application_method": "LH 청약플러스 또는 관할 센터 문의",
        "required_documents": DOC_PLACEHOLDER,
        "category": "HOUSING",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "LH 임대주택 에너지 자립생활 안정자금 주거 생활안정 공공임대 40만원",
        "organization": "한국토지주택공사(LH)",
        "region_sido": None,
        "support_amount": "1인당 40만원",
        "application_start": None,
        "application_end": None,
    },
    {
        "title": "삼성 희망디딤돌 자립준비청년 취업지원사업",
        "summary": "자립준비청년을 위한 직무교육, 기숙사 지원 및 월 100만 원 교육수당 지원",
        "content": (
            "전문 직무 교육과 인턴십 지원\n"
            "- 모집 직종: 공조냉동, 디자인, 전기설비, 중장비, 제과제빵, 펫케어\n"
            "- 지원 내용: 직무교육/자격증, 교육수당(월 최대 100만 원), 기숙사 전액 지원, "
            "삼성관계사 멘토링/인턴십, 심리정서지원"
        ),
        "eligibility": "만 34세 이하 미취업 자립준비청년 (보호종료 5년 경과자 등 포함)",
        "eligibility_items": [
            "만 34세 이하 자립준비청년",
            "미취업 상태",
            "보호종료 5년 경과자도 지원 가능",
        ],
        "application_method": "희망디딤돌 홈페이지 가입 후 직무교육 신청",
        "required_documents": DOC_PLACEHOLDER,
        "category": "EMPLOYMENT",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "삼성 희망디딤돌 취업 직무교육 인턴십 자격증 기숙사 교육수당 미취업 공조냉동 디자인 전기설비 중장비 제과제빵 펫케어",
        "organization": "삼성희망디딤돌",
        "region_sido": None,
        "support_amount": "교육수당 월 최대 100만원 (기숙사 전액 지원 별도)",
        "application_start": date(2026, 3, 17),
        "application_end": date(2026, 4, 30),
    },
    {
        "title": "자립정보ON 및 자립준비청년 상담/멘토링 서비스",
        "summary": "자립준비청년 선배의 멘토링 및 온라인 정보 플랫폼, 맞춤형 콜센터 상담",
        "content": (
            "1. 바람개비서포터스: 선배 멘토링, 교육, 심리정서 지원, 자조모임\n"
            "2. 자립정보ON: 온라인 자립 정보 통합 플랫폼\n"
            "3. 자립준비청년 상담센터: 선배 상담원의 개별 상황(소득/주거/진학) 맞춤 상담 (평일 9시~18시)"
        ),
        "eligibility": "자립정보가 필요한 보호대상아동 및 자립준비청년",
        "eligibility_items": [
            "자립정보가 필요한 보호대상아동 또는 자립준비청년",
        ],
        "application_method": "자립정보ON 접속 또는 상담센터 전화",
        "required_documents": DOC_PLACEHOLDER,
        "category": "MENTAL_HEALTH",
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": "자립정보ON 바람개비서포터즈 멘토링 상담 심리정서 자조모임 콜센터 정보 플랫폼",
        "organization": "아동권리보장원",
        "region_sido": None,
        "support_amount": None,
        "application_start": None,
        "application_end": None,
    },
]


# ---------------------------------------------------------------------------
# 2) 통합일정표 엑셀 (제도명 + 모집 시작/마감일만 존재)
#    category 는 제도명 키워드로 분류했고, 상세 항목은 엑셀에 없으므로
#    지어내지 않고 "미확보" 상태임을 본문에 명시한다.
# ---------------------------------------------------------------------------
SCHEDULE_ONLY_POLICIES = [
    ("자립정착금 지원사업", "FINANCE", date(2026, 8, 1), date(2026, 11, 30)),
    ("디딤씨앗통장(아동발달지원계좌) 매칭 지원", "FINANCE", date(2026, 9, 1), date(2026, 9, 20)),
    ("국민기초생활보장 청년소득공제 특례", "FINANCE", date(2026, 10, 5), date(2026, 10, 25)),
    ("자립준비청년 SOS 긴급지원사업", "FINANCE", date(2026, 11, 1), date(2026, 11, 30)),
    ("LH 공공임대주택 우선공급 제도", "HOUSING", date(2026, 9, 15), date(2026, 9, 30)),
    ("청년 전세임대주택 융자지원 사업", "HOUSING", date(2026, 11, 1), date(2026, 11, 15)),
    ("지자체 청년 부동산 중개보수/이사비 지원", "HOUSING", date(2026, 10, 15), date(2026, 11, 15)),
    ("자립준비청년 월세 한시 특별지원사업", "HOUSING", date(2026, 8, 10), date(2026, 8, 31)),
    ("국가장학금 자립준비청년 우선선발 지원", "EDUCATION", date(2026, 11, 20), date(2026, 12, 15)),
    ("취업 후 상환 학자금 생활비 대출 무이자 지원", "EDUCATION", date(2026, 12, 1), date(2026, 12, 20)),
    ("자립준비청년 대학생 생활지원 장학사업", "EDUCATION", date(2026, 9, 10), date(2026, 10, 10)),
    ("국민취업지원제도(자립준비청년 특례) 사업", "EMPLOYMENT", date(2026, 10, 1), date(2026, 10, 31)),
    ("자립준비청년 직업훈련비 및 면접비 지원", "EMPLOYMENT", date(2026, 8, 15), date(2026, 9, 15)),
    ("공공기관·기업 연계 맞춤형 일경험 인턴십", "EMPLOYMENT", date(2026, 9, 20), date(2026, 10, 20)),
    ("전국민 마음투자 심리상담 바우처 지원", "MENTAL_HEALTH", date(2026, 12, 1), date(2026, 12, 20)),
    ("바람개비서포터즈 활동 지원사업", "MENTAL_HEALTH", date(2026, 8, 20), date(2026, 8, 31)),
    ("자립준비청년 문화·힐링 캠프 지원 프로그램", "MENTAL_HEALTH", date(2026, 10, 20), date(2026, 11, 5)),
]


def _build_schedule_policy(title, category, start, end):
    period = "{:%Y-%m-%d} ~ {:%Y-%m-%d}".format(start, end)
    return {
        "title": title,
        "summary": "모집 기간 {}. 상세 내용은 준비 중입니다.".format(period),
        "content": (
            "모집 기간: {}\n".format(period)
            + "통합일정표에서 확보한 모집 일정만 등록된 정책입니다. "
            "상세 지원 내용은 추후 보완 예정입니다."
        ),
        "eligibility": "지원 대상 정보가 아직 등록되지 않았습니다. 신청 기관 안내를 확인해 주세요.",
        "eligibility_items": [],
        "application_method": "신청 기관 안내를 확인해 주세요.",
        "required_documents": DOC_PLACEHOLDER,
        "category": category,
        "protection_types": [],
        "age_ranges": [],
        "income_criteria": [],
        "target_condition": title,
        "organization": "미정",
        "region_sido": None,
        "support_amount": None,
        "application_start": start,
        "application_end": end,
    }


def _all_rows():
    rows = list(DETAILED_POLICIES)
    rows += [_build_schedule_policy(*row) for row in SCHEDULE_ONLY_POLICIES]
    return rows


def load_policies(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for row in _all_rows():
        defaults = {key: value for key, value in row.items() if key != "title"}
        defaults["required_document_items"] = []
        Policy.objects.update_or_create(title=row["title"], defaults=defaults)


def unload_policies(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")
    titles = [row["title"] for row in _all_rows()]
    Policy.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0014_alter_curationmatchcache_cache_type"),
    ]

    operations = [
        migrations.RunPython(load_policies, unload_policies),
    ]
