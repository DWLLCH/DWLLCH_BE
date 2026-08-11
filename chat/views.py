from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import RiskCheckMessage, RiskCheckSession
from chat.serializers import (
    MessageCreateSerializer,
    RiskCheckMessageSerializer,
    RiskCheckSessionDetailSerializer,
    RiskCheckSessionSerializer,
)
from chat.services import analyze_risk


class RiskCheckSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = RiskCheckSession.objects.create(user=request.user)
        serializer = RiskCheckSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RiskCheckSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(
            RiskCheckSession, id=session_id, user=request.user
        )
        serializer = RiskCheckSessionDetailSerializer(session)
        return Response(serializer.data)


class RiskCheckMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(
            RiskCheckSession, id=session_id, user=request.user
        )

        input_serializer = MessageCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        content = input_serializer.validated_data["content"]

        user_message = RiskCheckMessage.objects.create(
            session=session,
            sender=RiskCheckMessage.Sender.USER,
            content=content,
        )

        # AI 분석 (현재는 스텁, API 확정 후 내부 구현만 교체)
        result = analyze_risk(content)
        user_message.risk_level = result.risk_level
        user_message.analysis_result = result.raw_response
        user_message.save(update_fields=["risk_level", "analysis_result"])

        session.latest_risk_level = result.risk_level
        session.save(update_fields=["latest_risk_level", "updated_at"])

        serializer = RiskCheckMessageSerializer(user_message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)