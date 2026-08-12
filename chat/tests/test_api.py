import base64
import tempfile
from datetime import date
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from chat.models import (
    RiskCheckMessage,
    RiskCheckMessageReport,
    RiskCheckSession,
    StructuredRiskReport,
    SupportConnection,
)
from chat.services import (
    ExternalAppLink,
    RiskAnalysisResult,
    StructuredReportResult,
)
from users.models import User


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RiskCheckAPITestCase(APITestCase):
    def setUp(self):
        self.user = self.create_user("owner@example.com", "owner")
        self.other_user = self.create_user("other@example.com", "other")
        self.client.force_authenticate(self.user)

    def create_user(self, email, username):
        return User.objects.create_user(
            email=email,
            username=username,
            password="password123!",
            birth_date=date(2000, 1, 1),
            protection_end_date=date(2028, 12, 31),
            sido="서울특별시",
            sigungu="동대문구",
            housing_type=User.HousingType.MONTHLY_RENT,
            income_type=User.IncomeType.EARNED,
            employment_type=User.EmploymentType.PART_TIME,
            education_status=User.EducationStatus.ENROLLED,
        )

    def create_session(self, user=None, risk_level=RiskCheckSession.RiskLevel.NONE):
        return RiskCheckSession.objects.create(
            user=user or self.user,
            latest_risk_level=risk_level,
        )

    def analysis_result(self, **overrides):
        values = {
            "risk_level": "HIGH",
            "summary": "전세사기 의심 신호가 있어 추가 확인을 권장합니다.",
            "flagged_clauses": ["보증금을 먼저 보내세요"],
            "missing_verifications": ["등기부등본 미확인"],
            "action_guide": ["계약을 보류하고 등기부등본을 확인하세요."],
            "external_app_link": ExternalAppLink(
                name="안심전세",
                url="https://www.khug.or.kr/jeonse/",
            ),
            "reply": "계약 전에 등기부등본과 임대인 정보를 확인해 주세요.",
            "suggested_replies": ["등기부등본 확인 방법", "계약서 사진 올리기"],
            "image_readable": True,
        }
        values.update(overrides)
        return RiskAnalysisResult(**values)

    def test_session_create_and_detail_use_common_response_format(self):
        create_response = self.client.post("/chat/risk-check/sessions", {}, format="json")

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create_response.data["success"])
        self.assertEqual(create_response.data["code"], "SUCCESS")
        session_id = create_response.data["data"]["id"]

        detail_response = self.client.get(f"/chat/risk-check/sessions/{session_id}")

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["data"]["messages"], [])

    def test_other_users_session_is_hidden(self):
        session = self.create_session(user=self.other_user)

        response = self.client.get(f"/chat/risk-check/sessions/{session.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "COMMON_404_NOT_FOUND")

    @patch("chat.views.analyze_risk")
    def test_text_message_saves_user_and_assistant_messages(self, analyze_risk):
        analyze_risk.return_value = self.analysis_result()
        session = self.create_session()

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {"type": "TEXT", "content": "집주인이 보증금을 먼저 보내라고 해요."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["riskLevel"], "HIGH")
        self.assertEqual(response.data["data"]["analysis"]["missingVerifications"], ["등기부등본 미확인"])
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(
            list(session.messages.values_list("sender", flat=True)),
            [RiskCheckMessage.Sender.USER, RiskCheckMessage.Sender.ASSISTANT],
        )
        session.refresh_from_db()
        self.assertEqual(session.latest_risk_level, RiskCheckSession.RiskLevel.HIGH)

    def test_text_message_rejects_image_file(self):
        session = self.create_session()
        image = SimpleUploadedFile(
            "contract.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type="image/png",
        )

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {
                "type": "TEXT",
                "content": "텍스트 메시지입니다.",
                "file": image,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(session.messages.count(), 0)

    @patch("chat.views.analyze_risk")
    def test_ai_failure_does_not_leave_duplicate_user_message(self, analyze_risk):
        analyze_risk.side_effect = RuntimeError("temporary failure")
        session = self.create_session()

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {"type": "TEXT", "content": "분석해 주세요."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["code"], "CHAT_503_AI_SERVICE_UNAVAILABLE")
        self.assertEqual(session.messages.count(), 0)

    @patch("chat.views.analyze_risk")
    def test_unreadable_image_returns_422_and_is_not_saved(self, analyze_risk):
        analyze_risk.return_value = self.analysis_result(image_readable=False)
        session = self.create_session()
        image = SimpleUploadedFile(
            "contract.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type="image/png",
        )

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {"type": "IMAGE", "content": "계약서입니다.", "file": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "CHAT_422_IMAGE_UNREADABLE")
        self.assertEqual(session.messages.count(), 0)

    def test_message_report_and_duplicate_report(self):
        session = self.create_session()
        message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.ASSISTANT,
            content="AI 응답",
        )
        url = f"/chat/risk-check/messages/{message.id}/report"

        first = self.client.post(url, {"reason": "판단이 실제와 달라요."}, format="json")
        second = self.client.post(url, {"reason": "다시 신고합니다."}, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second.data["code"], "CHAT_400_ALREADY_REPORTED")
        self.assertEqual(RiskCheckMessageReport.objects.count(), 1)

    @patch("chat.views.structure_session")
    def test_structure_session_returns_report_and_missing_fields(self, structure_session):
        structure_session.return_value = StructuredReportResult(
            date="",
            amount="5000000",
            location="서울특별시",
            counterpart="임대인",
            situation_summary="보증금 선입금을 요구받은 상황",
            risk_type="전세사기 의심",
            risk_grade="HIGH",
            missing_fields=["date"],
        )
        session = self.create_session()
        RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            content="보증금 500만원을 먼저 보내라고 합니다.",
        )

        response = self.client.post(f"/chat/sos/sessions/{session.id}/structure", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["missingFields"], ["date"])
        self.assertTrue(StructuredRiskReport.objects.filter(session=session).exists())
        session.refresh_from_db()
        self.assertEqual(session.status, RiskCheckSession.Status.STRUCTURED)

    def test_connect_requires_consent_for_noncritical_session(self):
        session = self.create_session(risk_level=RiskCheckSession.RiskLevel.HIGH)

        response = self.client.post(
            f"/chat/sos/sessions/{session.id}/connect",
            {"consent": False, "connectTo": "SUPPORT_STAFF"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "CHAT_400_CONSENT_REQUIRED")
        self.assertFalse(SupportConnection.objects.filter(session=session).exists())

    def test_connect_with_consent_records_connection(self):
        session = self.create_session(risk_level=RiskCheckSession.RiskLevel.HIGH)

        response = self.client.post(
            f"/chat/sos/sessions/{session.id}/connect",
            {"consent": True, "connectTo": "SUPPORT_STAFF"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["connected"])
        self.assertFalse(response.data["data"]["forcedConnection"])
        connection = SupportConnection.objects.get(session=session)
        self.assertTrue(connection.consent)

    def test_critical_session_forces_connection_without_consent(self):
        session = self.create_session(risk_level=RiskCheckSession.RiskLevel.CRITICAL)

        response = self.client.post(
            f"/chat/sos/sessions/{session.id}/connect",
            {"consent": False, "connectTo": "EMERGENCY"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["forcedConnection"])
        self.assertIn("notice", response.data["data"])
        connection = SupportConnection.objects.get(session=session)
        self.assertTrue(connection.forced_connection)
