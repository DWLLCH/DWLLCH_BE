# -*- coding: utf-8 -*-
"""서류 준비 가이드 텍스트를 정책별 제출서류 항목으로 채운다.

home/data 의 "서류준비가이드 텍스트 내용 정리.xlsx" 를 옮긴 것으로,
엑셀 컬럼과 항목 키는 아래와 같이 대응한다.

    서류 이름            -> label
    서류 내용 (무엇인지)  -> description
    발급 방법            -> issueMethod
    준비물               -> preparation
    신청 사이트 / 발급처  -> issuer
    사이트 URL           -> linkUrl

"준비 현황" 컬럼은 사용자마다 달라지는 값이라 옮기지 않는다(엑셀에는 전부 X).
정책은 title 이 아니라 policy_id 로 찾는다. 엑셀의 정책명이 우리 title 과
축약형으로 달라서, 이름이 바뀌어도 끊기지 않는 키를 쓴다.

엑셀 원본은 gitignore 대상(home/data/)이라 파싱 결과를 인라인한다.
"""

from django.db import migrations


DOCUMENTS_BY_POLICY_ID = {
    "POL-CEN-001": [
        {
            "label": "자립수당 신청서",
            "description": "자립수당을 신청하기 위해 작성하는 공식 신청서",
            "issueMethod": "행정복지센터 방문 또는 복지로 온라인 신청",
            "preparation": "신분증, 본인 명의 계좌 정보 등",
            "issuer": "복지로",
            "linkUrl": "https://www.bokjiro.go.kr",
        },
        {
            "label": "신분증",
            "description": "신청자의 본인 확인을 위한 신분증",
            "issueMethod": "본인이 소지",
            "preparation": "주민등록증·운전면허증·여권 등 유효한 신분증",
            "issuer": None,
            "linkUrl": None,
        },
        {
            "label": "사이버교육 이수증",
            "description": "자립·금융 관련 온라인 교육을 이수했음을 확인하는 증명자료",
            "issueMethod": "온라인 교육 이수 후 이수증 발급",
            "preparation": "본인 인증",
            "issuer": "서민금융진흥원 금융교육포털 / 국가아동권리보장원",
            "linkUrl": "https://edu.kinfa.or.kr",
        },
        {
            "label": "종합재무상담 확인서",
            "description": "종합재무상담을 받았음을 확인하는 자료",
            "issueMethod": "국민연금공단 상담 후 발급",
            "preparation": "본인 확인",
            "issuer": "국민연금공단",
            "linkUrl": "https://www.nps.or.kr",
        },
        {
            "label": "통장사본",
            "description": "자립수당을 지급받을 본인 명의 계좌를 확인하는 자료",
            "issueMethod": "본인 명의 통장 또는 은행 앱에서 계좌정보 확인",
            "preparation": "본인 명의 계좌",
            "issuer": "본인 거래 은행",
            "linkUrl": None,
        },
        {
            "label": "보호종료확인서",
            "description": "보호종료 사실과 자립준비청년 여부를 확인하는 자료",
            "issueMethod": "보호기관 또는 가정위탁지원센터에 문의·발급",
            "preparation": "본인 확인 및 보호이력 확인",
            "issuer": "보호기관 / 가정위탁지원센터",
            "linkUrl": None,
        },
    ],
    "POL-LOC-CN01": [
        {
            "label": "자립수당 신청서",
            "description": "충남 자립준비청년 지원 중 자립수당을 신청하기 위한 신청서",
            "issueMethod": "관할 읍면동 행정복지센터에서 작성·제출",
            "preparation": "신분증 등 본인 확인 자료",
            "issuer": "관할 읍면동 행정복지센터",
            "linkUrl": None,
        },
        {
            "label": "자립정착금 사용계획서",
            "description": "자립정착금을 어떤 목적으로 사용할지 작성하는 계획서",
            "issueMethod": "관할 기관에서 양식 확인 후 작성",
            "preparation": "지원금 사용계획",
            "issuer": "관할 행정복지센터 / 자립지원기관",
            "linkUrl": None,
        },
        {
            "label": "보호종료 확인 관련 서류",
            "description": "자립준비청년의 보호종료 사실을 확인하는 증빙자료",
            "issueMethod": "보호기관 또는 행정기관에 문의",
            "preparation": "보호이력 확인",
            "issuer": "보호기관 / 행정기관",
            "linkUrl": None,
        },
        {
            "label": "통장사본",
            "description": "지원금 지급을 위한 본인 명의 계좌 확인 자료",
            "issueMethod": "본인 명의 통장 준비 또는 은행 앱에서 확인",
            "preparation": "본인 명의 계좌",
            "issuer": "본인 거래 은행",
            "linkUrl": None,
        },
        {
            "label": "대학 재학·진학 관련 증빙",
            "description": "대학생활안정자금 대상 여부를 확인하기 위한 증빙자료",
            "issueMethod": "재학 중인 대학에서 재학증명서 등 발급",
            "preparation": "학교 정보",
            "issuer": "해당 대학",
            "linkUrl": None,
        },
    ],
    "POL-LOC-CN02": [
        {
            "label": "자립지원 신청서",
            "description": "맞춤형 자립지원통합서비스 신청을 위한 신청서",
            "issueMethod": "충남 자립지원전담기관 또는 관할 행정복지센터에서 작성",
            "preparation": "본인 확인 정보",
            "issuer": "충남 자립지원전담기관 / 행정복지센터",
            "linkUrl": None,
        },
        {
            "label": "자립기술평가 관련 자료",
            "description": "맞춤형 지원 대상 선정을 위해 자립 수준과 필요한 지원을 확인하는 자료",
            "issueMethod": "신청 과정에서 기관 안내에 따라 작성·제출",
            "preparation": "자립상황 및 필요 지원 정보",
            "issuer": "충남 자립지원전담기관",
            "linkUrl": None,
        },
        {
            "label": "개인정보 수집·이용 동의서",
            "description": "지원사업 심사와 서비스 제공을 위해 개인정보 이용에 동의하는 서류",
            "issueMethod": "신청기관에서 제공하는 양식 작성",
            "preparation": "본인 서명",
            "issuer": "충남 자립지원전담기관",
            "linkUrl": None,
        },
        {
            "label": "보호종료 확인 관련 서류",
            "description": "지원 대상인 보호종료 5년 이내 자립준비청년임을 확인하는 자료",
            "issueMethod": "행정정보 확인이 어려운 경우 보호기관에 문의",
            "preparation": "보호이력 확인",
            "issuer": "보호기관",
            "linkUrl": None,
        },
    ],
    "POL-LOC-GB01": [
        {
            "label": "자립수당 신청서",
            "description": "경북 자립준비청년 자립수당을 신청하기 위한 신청서",
            "issueMethod": "관할 시·군 주민센터에서 작성·제출",
            "preparation": "신분증 등 본인 확인 자료",
            "issuer": "관할 시·군 주민센터",
            "linkUrl": None,
        },
        {
            "label": "신분증",
            "description": "신청자의 본인 확인을 위한 신분증",
            "issueMethod": "본인이 소지",
            "preparation": "유효한 신분증",
            "issuer": None,
            "linkUrl": None,
        },
        {
            "label": "사이버교육 이수증 또는 재무상담 확인서",
            "description": "자립 관련 교육 또는 재무상담 이수 여부를 확인하는 자료",
            "issueMethod": "온라인 교육 또는 상담 후 발급",
            "preparation": "본인 인증",
            "issuer": "온라인 교육기관 / 상담기관",
            "linkUrl": None,
        },
        {
            "label": "통장사본",
            "description": "자립수당 지급을 위한 본인 명의 계좌 확인 자료",
            "issueMethod": "본인 명의 통장 준비 또는 은행 앱에서 확인",
            "preparation": "본인 명의 계좌",
            "issuer": "본인 거래 은행",
            "linkUrl": None,
        },
        {
            "label": "보호종료확인서",
            "description": "보호종료 사실을 확인하는 증빙자료",
            "issueMethod": "행정정보 확인이 어려운 경우 보호기관에 문의",
            "preparation": "보호이력 확인",
            "issuer": "보호기관",
            "linkUrl": None,
        },
    ],
    "POL-PRV-001": [
        {
            "label": "지원 신청 정보/신청서",
            "description": "에너지 자립생활 안정자금 지원을 신청하기 위한 정보 또는 신청서",
            "issueMethod": "LH 유스타트 주거·생활지원 플랫폼에서 온라인 신청",
            "preparation": "본인 인증 및 신청 정보",
            "issuer": "LH 유스타트",
            "linkUrl": "https://apply.lh.or.kr",
        },
        {
            "label": "LH 임대주택 입주·계약 관련 정보",
            "description": "LH 임대주택 거주 또는 입주 예정 여부를 확인하는 정보",
            "issueMethod": "LH 보유 정보로 확인되는 경우 별도 발급 불필요",
            "preparation": "LH 임대주택 계약·입주 정보",
            "issuer": "LH",
            "linkUrl": "https://apply.lh.or.kr",
        },
        {
            "label": "자립준비청년 자격 증빙",
            "description": "자립준비청년 해당 여부를 확인하는 증빙자료",
            "issueMethod": "LH 안내에 따라 필요한 경우 제출",
            "preparation": "보호종료 등 자격 확인 자료",
            "issuer": "LH / 보호기관 / 행정기관",
            "linkUrl": "https://apply.lh.or.kr",
        },
        {
            "label": "본인 명의 계좌 정보",
            "description": "지원금 지급을 위한 본인 명의 계좌 정보",
            "issueMethod": "신청 과정에서 입력",
            "preparation": "본인 명의 계좌",
            "issuer": "본인 거래 은행",
            "linkUrl": None,
        },
    ],
    "POL-PRV-002": [
        {
            "label": "온라인 참가신청",
            "description": "직무교육 참가를 신청하기 위한 온라인 신청 정보",
            "issueMethod": "희망디딤돌 홈페이지 회원가입 후 직무교육 신청",
            "preparation": "회원가입 및 본인 정보",
            "issuer": "희망디딤돌",
            "linkUrl": "http://jarip-hope.or.kr",
        },
        {
            "label": "자립준비청년 자격 증빙",
            "description": "자립준비청년 대상 여부를 확인하기 위한 증빙자료",
            "issueMethod": "사업 공고에서 요구하는 경우 제출",
            "preparation": "보호종료 등 자격 확인 자료",
            "issuer": "사업기관 / 보호기관",
            "linkUrl": "http://jarip-hope.or.kr",
        },
        {
            "label": "미취업 상태 확인 자료",
            "description": "미취업 상태를 확인하기 위한 자료",
            "issueMethod": "사업 신청 과정에서 요구 여부 확인",
            "preparation": "사업기관 안내에 따른 자료",
            "issuer": "사업기관",
            "linkUrl": "http://jarip-hope.or.kr",
        },
        {
            "label": "개인정보 수집·이용 동의서",
            "description": "지원사업 참여를 위한 개인정보 이용 동의서",
            "issueMethod": "온라인 신청 과정에서 작성",
            "preparation": "본인 동의",
            "issuer": "사업기관",
            "linkUrl": "http://jarip-hope.or.kr",
        },
        {
            "label": "교육·자격 관련 서류",
            "description": "직무교육 및 선발 과정에서 필요한 학력·자격 등을 확인하는 자료",
            "issueMethod": "해당 직무 및 선발 과정에서 요구 시 제출",
            "preparation": "해당 자격·교육 이력",
            "issuer": "사업기관",
            "linkUrl": "http://jarip-hope.or.kr",
        },
    ],
    "INFO-BAS-001": [
        {
            "label": "기본 상담 신청 정보",
            "description": "개인의 상황에 맞는 자립정보 상담을 받기 위해 입력하는 기본 정보",
            "issueMethod": "자립정보ON 또는 상담센터에서 상담 신청",
            "preparation": "상담에 필요한 기본 정보",
            "issuer": "자립정보ON",
            "linkUrl": "https://jaripon.ncrc.or.kr",
        },
        {
            "label": "자립준비청년 확인자료",
            "description": "프로그램 참여 대상 여부를 확인하기 위한 자료",
            "issueMethod": "프로그램별 모집 공고에서 요구하는 경우 제출",
            "preparation": "보호종료 등 자격 확인 자료",
            "issuer": "자립정보ON / 보호기관 / 행정기관",
            "linkUrl": "https://jaripon.ncrc.or.kr",
        },
        {
            "label": "프로그램별 신청서",
            "description": "멘토링·교육 등 개별 프로그램 참여를 위한 신청서",
            "issueMethod": "자립정보ON 또는 해당 사업기관에서 제공하는 양식 작성",
            "preparation": "프로그램별 요구 정보",
            "issuer": "자립정보ON / 사업기관",
            "linkUrl": "https://jaripon.ncrc.or.kr",
        },
        {
            "label": "재학증명서 등 추가 증빙",
            "description": "특정 교육·장학 프로그램의 대상 여부를 확인하는 자료",
            "issueMethod": "학교에서 발급",
            "preparation": "재학 정보",
            "issuer": "해당 학교",
            "linkUrl": None,
        },
    ],
}


def load_required_documents(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for policy_id, documents in DOCUMENTS_BY_POLICY_ID.items():
        Policy.objects.filter(policy_id=policy_id).update(
            required_document_items=documents
        )


def clear_required_documents(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    Policy.objects.filter(policy_id__in=DOCUMENTS_BY_POLICY_ID).update(
        required_document_items=[]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0024_alter_policy_required_document_items"),
    ]

    operations = [
        migrations.RunPython(load_required_documents, clear_required_documents),
    ]
