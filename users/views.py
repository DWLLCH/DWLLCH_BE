from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta

from .models import User, RefreshToken as RefreshTokenModel
from .serializers import (
    SignupSerializer,
    EmailCheckSerializer,
    UsernameCheckSerializer,
    LoginSerializer,
    ReissueSerializer,
    PasswordChangeSerializer,
)

class SignupView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_400_INVALID_INPUT",
                    "message": "요청 값이 올바르지 않습니다.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "회원가입이 완료되었습니다.",
                "data": {
                    "userId": user.id,
                },
            },
            status=status.HTTP_201_CREATED,
        )

class EmailCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = EmailCheckSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_400_INVALID_INPUT",
                    "message": "이메일 형식이 올바르지 않습니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]

        if User.objects.filter(email=email).exists():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_409_CONFLICT",
                    "message": "이미 가입된 이메일입니다.",
                    "data": None,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "사용 가능한 이메일입니다.",
                "data": {
                    "available": True,
                },
            },
            status=status.HTTP_200_OK,
        )

class UsernameCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = UsernameCheckSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_400_INVALID_INPUT",
                    "message": "유저명 형식이 올바르지 않습니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = serializer.validated_data["username"]

        if User.objects.filter(username=username).exists():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_409_CONFLICT",
                    "message": "이미 사용 중인 유저명입니다.",
                    "data": None,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "사용 가능한 유저명입니다.",
                "data": {
                    "available": True,
                },
            },
            status=status.HTTP_200_OK,
        )

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request=request,
            username=email,
            password=password,
        )

        if user is None:
            return Response(
                {
                    "success": False,
                    "code": "AUTH_401_UNAUTHORIZED",
                    "message": "이메일 또는 비밀번호가 일치하지 않습니다.",
                    "data": None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        RefreshTokenModel.objects.update_or_create(     # DB에 refresh token 저장
            user=user,
            defaults={
                "token": refresh_token,
                "expires_at": timezone.now() + timedelta(days=14),
            },
        )
        
        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "로그인이 완료되었습니다.",
                "data": {
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "userId": user.id,
                },
            },
            status=status.HTTP_200_OK,
        )
    
class ReissueView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ReissueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refreshToken"]
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_400_INVALID_INPUT",
                    "message": "Refresh Token이 필요합니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            user_id = token["user_id"]
        except TokenError:
            return Response(
                {
                    "success": False,
                    "code": "AUTH_401_UNAUTHORIZED",
                    "message": "유효하지 않은 Refresh Token입니다.",
                    "data": None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            stored_token = RefreshTokenModel.objects.get(
                user_id=user_id
            )
        except RefreshTokenModel.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "code": "AUTH_401_UNAUTHORIZED",
                    "message": "로그인 정보가 존재하지 않습니다.",
                    "data": None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if stored_token.token != refresh_token:
            return Response(
                {
                    "success": False,
                    "code": "AUTH_401_UNAUTHORIZED",
                    "message": "유효하지 않은 Refresh Token입니다.",
                    "data": None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if stored_token.expires_at < timezone.now():
            return Response(
                {
                    "success": False,
                    "code": "AUTH_401_EXPIRED_TOKEN",
                    "message": "Refresh Token이 만료되었습니다.",
                    "data": None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        new_access_token = str(token.access_token)

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "Access Token이 재발급되었습니다.",
                "data": {
                    "accessToken": new_access_token,
                },
            },
            status=status.HTTP_200_OK,
        )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        RefreshTokenModel.objects.filter(
            user=request.user
        ).delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "code": "COMMON_400_INVALID_INPUT",
                    "message": "잘못된 요청입니다.",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_password = serializer.validated_data["currentPassword"]
        new_password = serializer.validated_data["newPassword"]

        user = request.user

        if not user.check_password(current_password):
            return Response(
                {
                    "success": False,
                    "code": "AUTH_400_CURRENT_PASSWORD_MISMATCH",
                    "message": "현재 비밀번호가 일치하지 않습니다.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        RefreshTokenModel.objects.filter(user=user).delete()

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "비밀번호가 변경되었습니다.",
                "data": {
                    "changed": True,
                    "changedAt": timezone.now(),
                    "otherSessionsRevoked": True,
                },
            },
            status=status.HTTP_200_OK,
        )