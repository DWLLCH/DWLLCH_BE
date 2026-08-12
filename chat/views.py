import logging

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import success_response
from chat.exceptions import (
    ConsentRequiredException,
    GeminiServiceUnavailableException,
    ImageUnreadableException,
)
from chat.models import (
    RiskCheckMessage,
    RiskCheckMessageReport,
    RiskCheckSession,
    StructuredRiskReport,
    SupportConnection,
)
from chat.serializers import (
    MessageCreateSerializer,
    MessageReportSerializer,
    RiskCheckMessageSerializer,
    RiskCheckSessionDetailSerializer,
    RiskCheckSessionSerializer,
    SupportConnectionSerializer,
)
from chat.services import analyze_risk, structure_session

logger = logging.getLogger(__name__)


class RiskCheckSessionCreateView(APIView):  # 세션 생성
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = RiskCheckSession.objects.create(user=request.user)
        serializer = RiskCheckSessionSerializer(session)
        return success_response(
            data=serializer.data,
            message="위기판독 세션이 생성되었습니다.",
            status_code=status.HTTP_201_CREATED,
        )


class RiskCheckSessionDetailView(APIView):  # 세션 상세 조회
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(
            RiskCheckSession.objects.prefetch_related("messages"),
            id=session_id,
            user=request.user,
        )
        serializer = RiskCheckSessionDetailSerializer(
            session,
            context={"request": request},
        )
        return success_response(data=serializer.data)


class RiskCheckMessageView(APIView):    # 메시지 목록 조회
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_session(self, request, session_id):
        return get_object_or_404(
            RiskCheckSession,
            id=session_id,
            user=request.user,
        )

    def get(self, request, session_id):
        session = self.get_session(request, session_id)
        messages = session.messages.all()

        serializer = RiskCheckMessageSerializer(
            messages,
            many=True,
            context={"request": request},
        )
        return success_response(data=serializer.data)

    def post(self, request, session_id):
        session = self.get_session(request, session_id)

        input_serializer = MessageCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        message_type = input_serializer.validated_data["type"]
        content = input_serializer.validated_data.get("content", "")
        uploaded_file = input_serializer.validated_data.get("file")

        previous_messages = list(
            session.messages.order_by("-created_at")[:20]
        )
        previous_messages.reverse()

        user_message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            type=message_type,
            content=content,
            file=uploaded_file,
        )

        try:
            result = analyze_risk(
                content=content,
                uploaded_file=user_message.file if uploaded_file else None,
                previous_messages=previous_messages,
            )
        except Exception as exc:
            logger.exception(
                "Gemini risk analysis failed: session_id=%s",
                session.id,
            )
            if user_message.file:
                user_message.file.delete(save=False)
            user_message.delete()
            raise GeminiServiceUnavailableException() from exc

        if message_type == RiskCheckMessage.MessageType.IMAGE:
            if not result.image_readable:
                if user_message.file:
                    user_message.file.delete(save=False)
                user_message.delete()
                raise ImageUnreadableException()

        analysis = {
            "summary": result.summary,
            "flaggedClauses": result.flagged_clauses,
            "missingVerifications": result.missing_verifications,
        }

        external_app_link = (
            result.external_app_link.model_dump()
            if result.external_app_link
            else None
        )

        user_message.risk_level = result.risk_level
        user_message.analysis_result = {
            **analysis,
            "actionGuide": result.action_guide,
            "externalAppLink": external_app_link,
            "imageReadable": result.image_readable,
        }
        user_message.save(
            update_fields=["risk_level", "analysis_result"]
        )

        assistant_message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.ASSISTANT,
            type=RiskCheckMessage.MessageType.TEXT,
            content=result.reply,
            risk_level=result.risk_level,
            analysis_result={
                "suggestedReplies": result.suggested_replies,
            },
        )

        session.latest_risk_level = result.risk_level
        session.save(update_fields=["latest_risk_level", "updated_at"])

        return success_response(
            data={
                "messageId": user_message.id,
                "assistantMessageId": assistant_message.id,
                "riskLevel": result.risk_level,
                 "analysis": analysis,
                 "actionGuide": result.action_guide,
                 "externalAppLink": external_app_link,
                 "reply": result.reply,
                 "suggestedReplies": result.suggested_replies,
                 },
                 message="메시지 전송 및 AI 분석이 완료되었습니다.",
                 status_code=status.HTTP_201_CREATED,
        )


class RiskCheckMessageReportView(APIView):  # 오류 신고
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            RiskCheckMessage,
            id=message_id,
            session__user=request.user,
        )

        serializer = MessageReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                report = RiskCheckMessageReport.objects.create(
                    message=message,
                    user=request.user,
                    reason=serializer.validated_data["reason"],
                )
        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "code": "CHAT_400_ALREADY_REPORTED",
                    "message": "이미 신고한 AI 판독 결과입니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data={
                "reportId": report.id,
                "reported": True,
                "createdAt": report.created_at,
                },
                message="AI 판독 오류가 신고되었습니다.",
                status_code=status.HTTP_201_CREATED,
                )


class RiskCheckStructureView(APIView):  # 상황 구조화
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(
            RiskCheckSession,
            id=session_id,
            user=request.user,
        )
        messages = list(session.messages.order_by("created_at"))

        if not messages:
            return Response(
                {
                    "success": False,
                    "code": "CHAT_400_EMPTY_SESSION",
                    "message": "구조화할 대화 내용이 없습니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = structure_session(messages)
        except Exception as exc:
            logger.exception(
                "Gemini session structuring failed: session_id=%s",
                session.id,
            )
            raise GeminiServiceUnavailableException() from exc

        report, _ = StructuredRiskReport.objects.update_or_create(
            session=session,
            defaults={
                "date": result.date,
                "amount": result.amount,
                "location": result.location,
                "counterpart": result.counterpart,
                "situation_summary": result.situation_summary,
                "risk_type": result.risk_type,
                "risk_grade": result.risk_grade,
                "missing_fields": result.missing_fields,
            },
        )

        session.latest_risk_level = result.risk_grade
        session.status = RiskCheckSession.Status.STRUCTURED
        session.save(
            update_fields=[
                "latest_risk_level",
                "status",
                "updated_at",
            ]
        )

        return success_response(
            data={
                "structuredReport": {
                    "date": report.date,
                    "amount": report.amount,
                    "location": report.location,
                    "counterpart": report.counterpart,
                    "situationSummary": report.situation_summary,
                    "riskType": report.risk_type,
                },
                "riskGrade": report.risk_grade,
                "missingFields": report.missing_fields,
            },
            message="상황 구조화가 완료되었습니다.",
        )


class RiskCheckConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(
            RiskCheckSession,
            id=session_id,
            user=request.user,
        )

        serializer = SupportConnectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consent = serializer.validated_data["consent"]
        connect_to = serializer.validated_data["connectTo"]
        forced_connection = (
            session.latest_risk_level
            == RiskCheckSession.RiskLevel.CRITICAL
        )

        if not consent and not forced_connection:
            raise ConsentRequiredException()

        notice = ""

        if forced_connection and not consent:
            notice = (
                "현재 대화에서 즉각적인 안전 위험 신호가 감지되어 "
                "사전 공개된 긴급 안전 정책에 따라 조력자 연계가 진행됩니다."
            )

        connection, _ = SupportConnection.objects.update_or_create(
            session=session,
            defaults={
                "connect_to": connect_to,
                "consent": consent,
                "forced_connection": forced_connection,
                "notice": notice,
            },
        )

        session.status = RiskCheckSession.Status.CONNECTED
        session.save(update_fields=["status", "updated_at"])

        response_data = {
            "connected": True,
            "connectedAt": connection.connected_at,
            "forcedConnection": forced_connection,
        }

        if notice:
            response_data["notice"] = notice

        return success_response(data=response_data,
                                message="조력자 연계가 완료되었습니다.")
