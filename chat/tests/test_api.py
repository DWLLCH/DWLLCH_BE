import base64
import io
import tempfile
import zipfile
from datetime import date
from unittest.mock import patch
from urllib.parse import urlsplit

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
    STRUCTURE_FIELD_NAMES,
    AttachmentUnreadableError,
    ExternalAppLink,
    GeminiRequestError,
    RiskAnalysisResult,
    StructuredReportResult,
    analyze_risk,
    is_ready_for_structure,
    normalize_collected_structure_fields,
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
            protection_type=User.ProtectionType.RESIDENTIAL_CARE,
            housing_type=User.HousingType.MONTHLY_RENT,
            housing_situation=User.HousingSituation.STABLE,
            living_status=[User.LivingStatus.EMPLOYED],
            income_type=User.IncomeType.EARNED,
            support_received=[User.SupportType.SETTLEMENT_FUND],
            needed_help=[User.NeededHelp.HOUSING],
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
        create_response = self.client.post(
            "/chat/risk-check/sessions",
            {},
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(create_response.data["success"])
        self.assertEqual(create_response.data["code"], "SUCCESS")

        session_data = create_response.data["data"]

        self.assertIn("latestRiskLevel", session_data)
        self.assertIn("createdAt", session_data)
        self.assertIn("updatedAt", session_data)

        self.assertNotIn("latest_risk_level", session_data)
        self.assertNotIn("created_at", session_data)
        self.assertNotIn("updated_at", session_data)

        session_id = session_data["id"]

        detail_response = self.client.get(
            f"/chat/risk-check/sessions/{session_id}"
        )

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
        )

        detail_data = detail_response.data["data"]

        self.assertIn("latestRiskLevel", detail_data)
        self.assertIn("createdAt", detail_data)
        self.assertIn("updatedAt", detail_data)

        self.assertNotIn("latest_risk_level", detail_data)
        self.assertNotIn("created_at", detail_data)
        self.assertNotIn("updated_at", detail_data)

        self.assertEqual(detail_data["messages"], [])
        
    def test_message_list_uses_camel_case_fields(self):
        session = self.create_session()

        RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=RiskCheckMessage.MessageType.TEXT,
            content="테스트 메시지",
            risk_level=RiskCheckSession.RiskLevel.HIGH,
            analysis_result={
                "summary": "테스트 분석 결과",
            },
        )

        response = self.client.get(
            f"/chat/risk-check/sessions/{session.id}/messages"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        message = response.data["data"][0]

        self.assertIn("fileUrl", message)
        self.assertIn("riskLevel", message)
        self.assertIn("analysisResult", message)
        self.assertIn("createdAt", message)

        self.assertNotIn("file_url", message)
        self.assertNotIn("risk_level", message)
        self.assertNotIn("analysis_result", message)
        self.assertNotIn("created_at", message)

        self.assertEqual(message["riskLevel"], "HIGH")
        self.assertEqual(
            message["analysisResult"],
            {
                "summary": "테스트 분석 결과",
            },
        )

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
        self.assertEqual(response.data["data"]["analysisResult"]["missingVerifications"], ["등기부등본 미확인"])
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
        analyze_risk.side_effect = GeminiRequestError("temporary failure")
        session = self.create_session()

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {"type": "TEXT", "content": "분석해 주세요."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["code"], "CHAT_503_AI_SERVICE_UNAVAILABLE")
        self.assertEqual(session.messages.count(), 0)

    def test_programming_error_is_not_reported_as_gemini_outage(self):
        session = self.create_session()

        with patch("chat.views.analyze_risk", side_effect=AttributeError("bug")):
            with self.assertRaises(AttributeError):
                self.client.post(
                    f"/chat/risk-check/sessions/{session.id}/messages",
                    {"type": "TEXT", "content": "분석해 주세요."},
                    format="json",
                )

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

    def test_other_user_cannot_access_session_bound_endpoints(self):
        session = self.create_session(user=self.other_user)
        message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.ASSISTANT,
            content="AI 응답",
        )

        requests = [
            self.client.post(
                f"/chat/risk-check/sessions/{session.id}/messages",
                {"type": "TEXT", "content": "접근 시도"},
                format="json",
            ),
            self.client.post(
                f"/chat/sos/sessions/{session.id}/structure",
                {},
                format="json",
            ),
            self.client.post(
                f"/chat/sos/sessions/{session.id}/connect",
                {"consent": True, "connectTo": "SUPPORT_STAFF"},
                format="json",
            ),
            self.client.post(
                f"/chat/risk-check/messages/{message.id}/report",
                {"reason": "접근 시도"},
                format="json",
            ),
        ]

        for response in requests:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

    @patch("chat.views.structure_session")
    def test_structure_preserves_existing_critical_risk(self, structure_session):
        structure_session.return_value = StructuredReportResult(
            risk_grade="HIGH",
            missing_fields=[],
        )
        session = self.create_session(
            risk_level=RiskCheckSession.RiskLevel.CRITICAL
        )
        RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            content="도움이 필요합니다.",
        )

        response = self.client.post(
            f"/chat/sos/sessions/{session.id}/structure",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(
            session.latest_risk_level,
            RiskCheckSession.RiskLevel.CRITICAL,
        )

    @patch("chat.views.structure_session")
    def test_structure_uses_only_latest_twenty_messages(self, structure_session):
        structure_session.return_value = StructuredReportResult(
            risk_grade="LOW",
            missing_fields=[],
        )
        session = self.create_session()
        for index in range(25):
            RiskCheckMessage.objects.create(
                session=session,
                sender=RiskCheckMessage.Sender.USER,
                content=f"message-{index}",
            )

        response = self.client.post(
            f"/chat/sos/sessions/{session.id}/structure",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        messages = structure_session.call_args.args[0]
        self.assertEqual(len(messages), 20)
        self.assertEqual(messages[0].content, "message-5")
        self.assertEqual(messages[-1].content, "message-24")

    def test_uploaded_file_requires_session_owner(self):
        session = self.create_session(user=self.other_user)
        image = SimpleUploadedFile(
            "contract.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type="image/png",
        )
        message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=RiskCheckMessage.MessageType.IMAGE,
            file=image,
        )

        response = self.client.get(
            f"/chat/risk-check/messages/{message.id}/file"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_signed_file_url_can_be_rendered_without_auth_header(self):
        session = self.create_session()
        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "contract.png",
            image_bytes,
            content_type="image/png",
        )
        RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=RiskCheckMessage.MessageType.IMAGE,
            file=image,
        )

        detail_response = self.client.get(
            f"/chat/risk-check/sessions/{session.id}"
        )
        file_url = detail_response.data["data"]["messages"][0]["fileUrl"]
        parsed_url = urlsplit(file_url)

        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"{parsed_url.path}?{parsed_url.query}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), image_bytes)

    def test_tampered_file_token_is_rejected(self):
        session = self.create_session()
        image = SimpleUploadedFile(
            "contract.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            content_type="image/png",
        )
        message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=RiskCheckMessage.MessageType.IMAGE,
            file=image,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/chat/risk-check/messages/{message.id}/file?token=tampered"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_owner_can_download_uploaded_file(self):
        session = self.create_session()
        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        image = SimpleUploadedFile(
            "contract.png",
            image_bytes,
            content_type="image/png",
        )
        message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=RiskCheckMessage.MessageType.IMAGE,
            file=image,
        )

        response = self.client.get(
            f"/chat/risk-check/messages/{message.id}/file"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(b"".join(response.streaming_content), image_bytes)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("inline", response["Content-Disposition"])

    @patch("chat.views.analyze_risk")
    def test_later_low_message_does_not_downgrade_critical_risk(
        self,
        analyze_risk,
    ):
        analyze_risk.return_value = self.analysis_result(risk_level="LOW")
        session = self.create_session(
            risk_level=RiskCheckSession.RiskLevel.CRITICAL
        )

        response = self.client.post(
            f"/chat/risk-check/sessions/{session.id}/messages",
            {"type": "TEXT", "content": "이제 괜찮은 것 같아요."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session.refresh_from_db()
        self.assertEqual(
            session.latest_risk_level,
            RiskCheckSession.RiskLevel.CRITICAL,
        )

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


class ReadyForStructureTests(APITestCase):
    """구조화 카드 자동 표시 기준(readyForStructure) 검증."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="ready@example.com",
            username="ready",
            password="password123!",
            birth_date=date(2000, 1, 1),
        )
        self.client.force_authenticate(self.user)
        self.session = RiskCheckSession.objects.create(user=self.user)

    def analysis_result(self, collected):
        return RiskAnalysisResult(
            risk_level="HIGH",
            summary="요약",
            reply="답변",
            collected_structure_fields=collected,
        )

    def send_message(self, collected):
        with patch("chat.views.analyze_risk") as analyze_risk:
            analyze_risk.return_value = self.analysis_result(collected)

            return self.client.post(
                f"/chat/risk-check/sessions/{self.session.id}/messages",
                {"type": "TEXT", "content": "상황을 설명합니다."},
                format="json",
            )

    def test_all_six_fields_collected_marks_ready(self):
        response = self.send_message(list(STRUCTURE_FIELD_NAMES))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        analysis = response.data["data"]["analysisResult"]
        self.assertTrue(analysis["readyForStructure"])
        self.assertEqual(
            analysis["collectedStructureFields"],
            list(STRUCTURE_FIELD_NAMES),
        )

    def test_missing_one_field_is_not_ready(self):
        response = self.send_message(list(STRUCTURE_FIELD_NAMES[:-1]))

        analysis = response.data["data"]["analysisResult"]
        self.assertFalse(analysis["readyForStructure"])
        self.assertNotIn("risk_type", analysis["collectedStructureFields"])

    def test_no_collected_fields_is_not_ready(self):
        response = self.send_message([])

        analysis = response.data["data"]["analysisResult"]
        self.assertFalse(analysis["readyForStructure"])
        self.assertEqual(analysis["collectedStructureFields"], [])

    def test_result_is_saved_on_the_message(self):
        """대화를 다시 불러와도 같은 판단을 쓸 수 있어야 한다."""
        self.send_message(list(STRUCTURE_FIELD_NAMES))

        message = RiskCheckMessage.objects.filter(
            session=self.session,
            sender=RiskCheckMessage.Sender.USER,
        ).latest("id")
        self.assertTrue(message.analysis_result["readyForStructure"])

    def test_unknown_or_duplicated_field_names_are_ignored(self):
        response = self.send_message(
            ["DATE", " amount ", "amount", "존재하지_않는_항목"]
        )

        analysis = response.data["data"]["analysisResult"]
        self.assertEqual(
            analysis["collectedStructureFields"],
            ["date", "amount"],
        )
        self.assertFalse(analysis["readyForStructure"])

    def test_normalize_helper_tolerates_unexpected_payloads(self):
        """스키마를 벗어난 응답이 와도 예외 없이 걸러져야 한다."""
        self.assertEqual(normalize_collected_structure_fields(None), [])
        self.assertEqual(normalize_collected_structure_fields("date"), [])
        self.assertEqual(
            normalize_collected_structure_fields([None, 3, "date"]),
            ["date"],
        )

    def test_normalize_helper_keeps_declared_order(self):
        collected = normalize_collected_structure_fields(
            ["risk_type", "amount", "date"]
        )

        self.assertEqual(collected, ["date", "amount", "risk_type"])
        self.assertFalse(is_ready_for_structure(collected))
        self.assertTrue(is_ready_for_structure(list(STRUCTURE_FIELD_NAMES)))


def build_docx(paragraphs):
    """Word 가 만드는 최소 구조의 DOCX 바이트를 만든다."""
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs
    )
    document = (
        '<?xml version="1.0"?>'
        f'<w:document xmlns:w="{namespace}"><w:body>{body}</w:body></w:document>'
    )

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)

    return buffer.getvalue()


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>"
DOCX_UPLOAD_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentUploadTests(APITestCase):
    """위기판독 문서(PDF/DOCX) 첨부."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="doc@example.com",
            username="docuser",
            password="password123!",
            birth_date=date(2000, 1, 1),
        )
        self.client.force_authenticate(self.user)
        self.session = RiskCheckSession.objects.create(user=self.user)

    def analysis_result(self, **overrides):
        values = {
            "risk_level": "HIGH",
            "summary": "요약",
            "reply": "답변",
        }
        values.update(overrides)
        return RiskAnalysisResult(**values)

    def post_file(self, uploaded, message_type="DOCUMENT"):
        return self.client.post(
            f"/chat/risk-check/sessions/{self.session.id}/messages",
            {
                "type": message_type,
                "content": "계약서 확인해 주세요.",
                "file": uploaded,
            },
            format="multipart",
        )

    @patch("chat.views.analyze_risk")
    def test_pdf_upload_is_accepted(self, analyze_risk):
        analyze_risk.return_value = self.analysis_result()

        response = self.post_file(
            SimpleUploadedFile(
                "계약서.pdf", PDF_BYTES, content_type="application/pdf"
            )
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = RiskCheckMessage.objects.get(
            id=response.data["data"]["messageId"]
        )
        self.assertEqual(message.type, RiskCheckMessage.MessageType.DOCUMENT)
        self.assertTrue(message.file.name.endswith(".pdf"))

    @patch("chat.views.analyze_risk")
    def test_docx_upload_is_accepted(self, analyze_risk):
        analyze_risk.return_value = self.analysis_result()

        response = self.post_file(
            SimpleUploadedFile(
                "계약서.docx",
                build_docx(["임대차계약서", "보증금 3,000만원"]),
                content_type=DOCX_UPLOAD_TYPE,
            )
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = RiskCheckMessage.objects.get(
            id=response.data["data"]["messageId"]
        )
        self.assertTrue(message.file.name.endswith(".docx"))

    @patch("chat.views.analyze_risk")
    def test_docx_text_is_passed_to_the_model(self, analyze_risk):
        """DOCX 는 모델이 못 읽으므로 본문이 프롬프트로 전달돼야 한다."""
        analyze_risk.return_value = self.analysis_result()

        self.post_file(
            SimpleUploadedFile(
                "계약서.docx",
                build_docx(["보증금 반환 특약 없음"]),
                content_type=DOCX_UPLOAD_TYPE,
            )
        )

        uploaded = analyze_risk.call_args.kwargs["uploaded_file"]
        self.assertTrue(uploaded.name.endswith(".docx"))

    @patch("chat.views.analyze_risk")
    def test_octet_stream_is_resolved_by_extension(self, analyze_risk):
        """브라우저가 형식을 안 알려줘도 확장자로 판별한다."""
        analyze_risk.return_value = self.analysis_result()

        response = self.post_file(
            SimpleUploadedFile(
                "계약서.pdf",
                PDF_BYTES,
                content_type="application/octet-stream",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unsupported_document_type_is_rejected(self):
        response = self.post_file(
            SimpleUploadedFile(
                "계약서.hwp", b"whatever", content_type="application/x-hwp"
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(RiskCheckMessage.objects.count(), 0)

    def test_extension_spoofed_file_is_rejected(self):
        """확장자만 pdf 로 바꾼 파일은 앞부분 검사에서 걸린다."""
        response = self.post_file(
            SimpleUploadedFile(
                "악성.pdf",
                b"MZ\x90\x00 this is not a pdf",
                content_type="application/pdf",
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(RiskCheckMessage.objects.count(), 0)

    def test_image_uploaded_as_document_is_rejected(self):
        response = self.post_file(
            SimpleUploadedFile("사진.png", PNG_BYTES, content_type="image/png")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_uploaded_as_image_is_rejected(self):
        response = self.post_file(
            SimpleUploadedFile(
                "계약서.pdf", PDF_BYTES, content_type="application/pdf"
            ),
            message_type="IMAGE",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fake_image_is_rejected(self):
        """FileField 로 바꾼 뒤에도 실제 이미지인지 확인한다."""
        response = self.post_file(
            SimpleUploadedFile(
                "가짜.png", b"not an image", content_type="image/png"
            ),
            message_type="IMAGE",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_without_file_is_rejected(self):
        response = self.client.post(
            f"/chat/risk-check/sessions/{self.session.id}/messages",
            {"type": "DOCUMENT", "content": "파일 없이 보냅니다."},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_docx_is_rejected_before_calling_the_model(self):
        """본문을 못 뽑으면 Gemini 클라이언트를 만들기 전에 끊는다."""
        empty_docx = SimpleUploadedFile(
            "빈문서.docx", build_docx([]), content_type=DOCX_UPLOAD_TYPE
        )

        with patch("chat.services._get_client") as get_client:
            with self.assertRaises(AttachmentUnreadableError):
                analyze_risk(content="", uploaded_file=empty_docx)

        get_client.assert_not_called()

    @patch("chat.views.analyze_risk")
    def test_unreadable_attachment_returns_422_and_is_not_saved(
        self, analyze_risk
    ):
        analyze_risk.side_effect = AttachmentUnreadableError

        response = self.post_file(
            SimpleUploadedFile(
                "빈문서.docx", build_docx([]), content_type=DOCX_UPLOAD_TYPE
            )
        )

        self.assertEqual(
            response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        self.assertEqual(response.data["code"], "CHAT_422_DOCUMENT_UNREADABLE")
        self.assertEqual(RiskCheckMessage.objects.count(), 0)

    @patch("chat.views.analyze_risk")
    def test_unreadable_document_returns_document_specific_error(
        self, analyze_risk
    ):
        analyze_risk.return_value = self.analysis_result(image_readable=False)

        response = self.post_file(
            SimpleUploadedFile(
                "계약서.pdf", PDF_BYTES, content_type="application/pdf"
            )
        )

        self.assertEqual(
            response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        self.assertEqual(response.data["code"], "CHAT_422_DOCUMENT_UNREADABLE")
        self.assertEqual(RiskCheckMessage.objects.count(), 0)

    @patch("chat.views.analyze_risk")
    def test_uploaded_document_is_served_with_its_own_type(self, analyze_risk):
        analyze_risk.return_value = self.analysis_result()
        self.post_file(
            SimpleUploadedFile(
                "계약서.pdf", PDF_BYTES, content_type="application/pdf"
            )
        )
        message = RiskCheckMessage.objects.get(
            sender=RiskCheckMessage.Sender.USER
        )

        response = self.client.get(
            f"/chat/risk-check/messages/{message.id}/file"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
