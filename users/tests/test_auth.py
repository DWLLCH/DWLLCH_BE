from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User


class AuthAPITestCase(APITestCase):

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123!",
            "passwordConfirm": "password123!",
        }
                    
    def create_test_user(self, **kwargs):
        defaults = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123!",
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
            "/auth/login",
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
            "/auth/signup",
            self.user_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            User.objects.filter(
                email="test@example.com"
            ).exists()
        )

        user = User.objects.get(
            email="test@example.com"
        )

        # 자립 프로필 없이 계정 생성되었는지 확인
        self.assertIsNone(user.birth_date)
        self.assertIsNone(user.protection_end_date)
        self.assertIsNone(user.protection_type)
        self.assertIsNone(user.protection_status)
        self.assertIsNone(user.housing_type)
        self.assertIsNone(user.housing_situation)
        self.assertIsNone(user.income_type)

        self.assertEqual(user.living_status, [])
        self.assertEqual(user.support_received, [])
        self.assertEqual(user.needed_help, [])

        self.assertFalse(user.profile_completed)

        # 회원가입 직후 인증 가능 여부
        self.assertIn(
            "accessToken",
            response.data["data"],
        )
        self.assertIn(
            "refreshToken",
            response.data["data"],
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())

    def test_email_duplicate_check(self):
        self.create_test_user(username="otheruser",)

        response = self.client.post(
            "/auth/signup/email/check",
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
            "/auth/signup/username/check",
            {"username": "testuser"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_login_success(self):
        self.create_test_user()

        response = self.client.post(
            "/auth/login",
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
            "/auth/login",
            {
                "email": "test@example.com",
                "password": "WrongPassword!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reissue_success(self): # Refresh Token으로 Access Token 재발급 성공
        _, refresh_token = self.get_tokens()

        response = self.client.post(
            "/auth/reissue",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("accessToken", response.data["data"])

        new_access_token = response.data["data"]["accessToken"]

        # 재발급된 Access Token이 실제로 유효한 JWT인지 확인
        token = AccessToken(new_access_token)
        self.assertEqual(
            str(token["user_id"]),
            str(User.objects.get(email="test@example.com").id),
        )

    def test_reissue_invalid_refresh_token(self): # 유효하지 않은 Refresh Token으로 재발급 실패
        self.create_test_user()

        response = self.client.post(
            "/auth/reissue",
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
            "/auth/logout",
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
            "/auth/logout",
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
            "/auth/reissue",
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
            "/auth/password",
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

        # 비밀번호 변경 후 기존 Refresh Token이 폐기되었는지 확인
        response = self.client.post(
            "/auth/reissue",
            {
                "refreshToken": refresh_token,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_email_change_success(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["email"],
            "new@example.com",
        )

        user = User.objects.get(username="testuser")
        self.assertEqual(
            user.email,
            "new@example.com",
        )

    def test_email_change_wrong_password_fail(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "WrongPassword!",
                "newEmail": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["code"],
            "AUTH_400_CURRENT_PASSWORD_MISMATCH",
        )

        user = User.objects.get(username="testuser")
        self.assertEqual(
            user.email,
            "test@example.com",
        )

    def test_email_change_duplicate_email_fail(self):
        access_token, _ = self.get_tokens()

        User.objects.create_user(
            email="existing@example.com",
            username="existinguser",
            password="Test1234!",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "existing@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        user = User.objects.get(username="testuser")
        self.assertEqual(
            user.email,
            "test@example.com",
        )

    def test_email_change_same_email_fail(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "test@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_email_change_invalid_email_fail(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "invalid-email",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_email_change_unauthenticated_fail(self):
        response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_with_new_email_after_change(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        change_response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            change_response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials()

        login_response = self.client.post(
            "/auth/login",
            {
                "email": "new@example.com",
                "password": "password123!",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "accessToken",
            login_response.data["data"],
        )

    def test_login_with_old_email_after_change_fail(self):
        access_token, _ = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        change_response = self.client.patch(
            "/auth/email",
            {
                "currentPassword": "password123!",
                "newEmail": "new@example.com",
            },
            format="json",
        )

        self.assertEqual(
            change_response.status_code,
            status.HTTP_200_OK,
        )

        self.client.credentials()

        login_response = self.client.post(
            "/auth/login",
            {
                "email": "test@example.com",
                "password": "password123!",
            },
            format="json",
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )




    def test_account_delete_success(self):
        access_token, refresh_token = self.get_tokens()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.delete(
            "/auth/account",
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