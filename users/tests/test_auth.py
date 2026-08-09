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
            "birthDate": date(2000, 1, 1),
            "protectionEndDate": date(2028, 12, 31),
            "sido": "서울특별시",
            "sigungu": "동대문구",
            "housingType": User.HousingType.MONTHLY_RENT,
            "incomeType": User.IncomeType.EARNED,
            "employmentType": User.EmploymentType.PART_TIME,
            "educationStatus": User.EducationStatus.ENROLLED,
        }

        defaults.update(kwargs)

        password = defaults.pop("password")

        return User.objects.create_user(
            password=password,
            **defaults,
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

    def test_protected_api_without_token(self):
        response = self.client.get("/api/v1/auth/test")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)