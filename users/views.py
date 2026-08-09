from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .models import User
from .serializers import SignupSerializer, EmailCheckSerializer, UsernameCheckSerializer, LoginSerializer

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

        return Response(
            {
                "success": True,
                "code": "SUCCESS",
                "message": "로그인이 완료되었습니다.",
                "data": {
                    "accessToken": str(refresh.access_token),
                    "refreshToken": str(refresh),
                    "userId": user.id,
                },
            },
            status=status.HTTP_200_OK,
        )