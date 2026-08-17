from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class OnboardingProfileTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="Test1234!",
        )

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        self.url = "/mypage/profile"

        self.valid_data = {
            "birthDate": "2003-05-20",
            "region": {
                "sido": "서울특별시",
                "sigungu": "성북구",
            },
            "protectionType": "RESIDENTIAL_CARE",
            "protectionStatus": "ENDED",
            "protectionEndDate": "2025-02-01",
            "housingType": "MONTHLY_RENT",
            "housingSituation": "STABLE",
            "livingStatus": [
                "SCHOOL",
                "PART_TIME",
            ],
            "incomeType": "EARNED",
            "supportReceived": [
                "INDEPENDENCE_ALLOWANCE",
            ],
            "neededHelp": [
                "HOUSING",
                "FINANCE",
            ],
        }

    def test_onboarding_profile_create_success(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.user.refresh_from_db()

        self.assertTrue(self.user.profile_completed)
        self.assertEqual(
            self.user.protection_status,
            User.ProtectionStatus.ENDED,
        )
        self.assertEqual(
            self.user.housing_type,
            User.HousingType.MONTHLY_RENT,
        )
        self.assertEqual(
            self.user.needed_help,
            ["HOUSING", "FINANCE"],
        )

    def test_onboarding_profile_duplicate_create_fail(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertEqual(
            response.data["code"],
            "PROFILE_409_ALREADY_COMPLETED",
        )

    def test_needed_help_max_three(self):
        data = self.valid_data.copy()

        data["neededHelp"] = [
            "HOUSING",
            "FINANCE",
            "EMPLOYMENT",
            "EDUCATION",
        ]

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_protected_status_without_end_date_success(self):
        data = self.valid_data.copy()

        data["protectionStatus"] = "PROTECTED"
        data.pop("protectionEndDate")

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.user.refresh_from_db()

        self.assertIsNone(
            self.user.protection_end_date
        )

    def test_scheduled_status_without_end_date_fail(self):
        data = self.valid_data.copy()

        data["protectionStatus"] = "SCHEDULED"
        data.pop("protectionEndDate")

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unauthenticated_profile_create_fail(self):
        self.client.credentials()

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_profile_patch_after_onboarding(self):
        self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        response = self.client.patch(
            self.url,
            {
                "housingType": "JEONSE",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.housing_type,
            User.HousingType.JEONSE,
        )

    def test_patch_protected_status_clears_end_date(self):
        self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        response = self.client.patch(
            self.url,
            {
                "protectionStatus": "PROTECTED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.protection_status,
            User.ProtectionStatus.PROTECTED,
        )
        self.assertIsNone(
            self.user.protection_end_date,
        )

    def test_patch_scheduled_without_end_date_fail(self):
        self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.client.patch(
            self.url,
            {
                "protectionStatus": "PROTECTED",
            },
            format="json",
        )

        response = self.client.patch(
            self.url,
            {
                "protectionStatus": "SCHEDULED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )