from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class AuthAPITestCase(APITestCase):

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123!",
            "passwordConfirm": "password123!",
            "birthDate": "2000-01-01",
            "protectionEndDate": "2028-12-31",
            "region": {
                "sido": "서울특별시",
                "sigungu": "동대문구",
            },
            "housingType": "MONTHLY_RENT",
            "incomeType": "EARNED",
            "employmentType": "PART_TIME",
            "educationStatus": "ENROLLED",
        }
                    
    def create_test_user(self, **kwargs):
        defaults = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123!",
            "birth_date": date(2000, 1, 1),
            "protection_end_date": date(2028, 12, 31),
            "sido": "서울특별시",
            "sigungu": "동대문구",
            "detail_address": None,
            "housing_type": User.HousingType.MONTHLY_RENT,
            "income_type": User.IncomeType.EARNED,
            "employment_type": User.EmploymentType.PART_TIME,
            "education_status": User.EducationStatus.ENROLLED,
        }

        defaults.update(kwargs)

        password = defaults.pop("password")

        return User.objects.create_user(
            password=password,
            **defaults,
        )

    def get_tokens(self):
        """테스트용 로그인 후 Access/Refresh Token 반환"""
        self.create_test_user()

        response = self.client.post(
            "/api/v1/auth/login",
            {
                "email": "test@example.com",
                "password": "password123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        return (
            response.data["data"]["accessToken"],
            response.data["data"]["refreshToken"],
        )
    
    def test_signup_success(self):
        response = self.client.post(
            "/api/v1/auth/signup",
            self.user_data,
            format="json",
        )

        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())

    def test_email_duplicate_check(self):
        self.create_test_user(username="otheruser",)

        response = self.client.post(
            "/api/v1/auth/signup/email/check",
            {"email": "test@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_username_duplicate_check(self):
        self.create_test_user(
            email="existing@example.com",
            username="testuser",
            password="Abcd1234!",
        )

        response = self.client.post(
            "/api/v1/auth/signup/username/check",
            {"username": "testuser"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_login_success(self):
        self.create_test_user()

        response = self.client.post(
            "/api/v1/auth/login",
            {
                "email": "test@example.com",
                "password": "password123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("accessToken", response.data["data"])
        self.assertIn("refreshToken", response.data["data"])

    def test_login_wrong_password(self):
        self.create_test_user(password="Abcd1234!",)

        response = self.client.post(
            "/api/v1/auth/login",
            {
                "email": "test@example.com",
                "password": "WrongPassword!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reissue_success(self): # Refresh Token으로 Access Token 재발급 성공
        access_token, refresh_token = self.get_tokens()

        response = self.client.post(
            "/api/v1/auth/reissue",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("accessToken", response.data["data"])

    def test_reissue_invalid_refresh_token(self): # 유효하지 않은 Refresh Token으로 재발급 실패
        self.create_test_user()

        response = self.client.post(
            "/api/v1/auth/reissue",
            {
                "refreshToken": "invalid-refresh-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertFalse(response.data["success"])

    def test_logout_success(self):
        access_token, refresh_token = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/v1/auth/logout",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_invalidates_refresh_token(self): # 로그아웃 후 기존 Refresh Token 사용 불가
        access_token, refresh_token = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        logout_response = self.client.post(
            "/api/v1/auth/logout",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # 로그아웃 후 같은 Refresh Token으로 재발급 시도
        reissue_response = self.client.post(
            "/api/v1/auth/reissue",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            reissue_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_password_change_success(self):
        access_token, refresh_token = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/api/v1/auth/password",
            {
                "currentPassword": "password123!",
                "newPassword": "NewPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        user = User.objects.get(email="test@example.com")
        self.assertTrue(
            user.check_password("NewPassword123!")
        )

    def test_account_delete_success(self):
        access_token, refresh_token = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.delete(
            "/api/v1/auth/account",
            {
                "password": "password123!",
                "reason": "서비스 이용 종료",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 사용자 삭제 확인
        self.assertFalse(
            User.objects.filter(email="test@example.com").exists()
        )