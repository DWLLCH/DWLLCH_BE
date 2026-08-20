from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from home.models import Policy
from home.services import (
    GeminiRequestError,
    PolicyMatchAssessment,
    PolicyMatchAssessmentResult,
)

from .models import Application, Notification

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

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

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
        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.user.refresh_from_db()

        self.assertTrue(self.user.profile_completed)
        self.assertEqual(self.user.protection_status, User.ProtectionStatus.ENDED)
        self.assertEqual(self.user.housing_type, User.HousingType.MONTHLY_RENT)
        self.assertEqual(self.user.needed_help, ["HOUSING", "FINANCE"])

    def test_onboarding_profile_duplicate_create_fail(self):
        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "PROFILE_409_ALREADY_COMPLETED")

    def test_needed_help_max_three(self):
        data = self.valid_data.copy()

        data["neededHelp"] = [
            "HOUSING",
            "FINANCE",
            "EMPLOYMENT",
            "EDUCATION",
        ]

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_protected_status_without_end_date_success(self):
        data = self.valid_data.copy()

        data["protectionStatus"] = "PROTECTED"
        data.pop("protectionEndDate")

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.user.refresh_from_db()

        self.assertIsNone(self.user.protection_end_date)

    def test_scheduled_status_without_end_date_fail(self):
        data = self.valid_data.copy()

        data["protectionStatus"] = "SCHEDULED"
        data.pop("protectionEndDate")

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_profile_create_fail(self):
        self.client.credentials()

        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_patch_after_onboarding(self):
        self.client.post(self.url, self.valid_data, format="json")

        response = self.client.patch(
            self.url,
            {"housingType": "JEONSE"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.housing_type, User.HousingType.JEONSE)

    def test_patch_protected_status_clears_end_date(self):
        self.client.post(self.url, self.valid_data, format="json")

        response = self.client.patch(
            self.url,
            {"protectionStatus": "PROTECTED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.protection_status, User.ProtectionStatus.PROTECTED)
        self.assertIsNone(self.user.protection_end_date)

    def test_patch_scheduled_without_end_date_fail(self):
        self.client.post(self.url, self.valid_data, format="json")

        self.client.patch(
            self.url,
            {"protectionStatus": "PROTECTED"},
            format="json",
        )

        response = self.client.patch(
            self.url,
            {"protectionStatus": "SCHEDULED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class NotificationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="notify@example.com",
            username="notifyuser",
            password="Test1234!",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="Test1234!",
        )

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        self.notification = Notification.objects.create(
            user=self.user,
            message="신청 마감이 3일 남았습니다.",
            type=Notification.Type.DEADLINE,
            target_id=10,
        )

        self.other_notification = Notification.objects.create(
            user=self.other_user,
            message="다른 사용자의 알림입니다.",
            type=Notification.Type.COMMENT,
            target_id=20,
        )

    def test_notification_list_contains_type_and_target_id(self):
        response = self.client.get("/mypage/notifications")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.data["content"]

        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["type"], Notification.Type.DEADLINE)
        self.assertEqual(content[0]["targetId"], 10)
        self.assertFalse(content[0]["isRead"])

    def test_notification_read_success(self):
        response = self.client.patch(
            f"/mypage/notifications/{self.notification.id}/read",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertTrue(response.data["data"]["isRead"])

    def test_cannot_read_other_users_notification(self):
        response = self.client.patch(
            f"/mypage/notifications/{self.other_notification.id}/read",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_notification_read_all_success(self):
        Notification.objects.create(
            user=self.user,
            message="두 번째 알림",
            type=Notification.Type.REPLY,
            target_id=30,
        )

        response = self.client.patch(
            "/mypage/notifications/read-all",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["updatedCount"], 2)

        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())

        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_unauthenticated_notification_read_fail(self):
        self.client.credentials()

        response = self.client.patch(
            f"/mypage/notifications/{self.notification.id}/read",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ApplicationMatchTest(APITestCase):
    """신청 목록의 AI 적합도와 마감일."""

    def setUp(self):
        self.url = "/mypage/applications"

        self.user = User.objects.create_user(
            email="application@example.com",
            username="applicationuser",
            password="Test1234!",
            profile_completed=True,
            sido="서울특별시",
            sigungu="동대문구",
            protection_status=User.ProtectionStatus.ENDED,
            living_status=[User.LivingStatus.JOB_SEEKING],
            needed_help=[User.NeededHelp.HOUSING],
            housing_situation=User.HousingSituation.BURDEN,
        )

        self.policy = Policy.objects.create(
            title="신청 대상 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            application_end=date(2026, 12, 31),
        )

        Application.objects.create(
            user=self.user,
            policy=self.policy,
            status=Application.Status.PLANNED,
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def match_result(self):
        return PolicyMatchAssessmentResult(
            matches=[
                PolicyMatchAssessment(
                    policy_id=self.policy.id,
                    match_level="HIGH",
                    match_reason="주거 상황과 잘 맞아요.",
                )
            ]
        )

    @patch("home.views.assess_policy_matches")
    def test_application_list_includes_match_and_deadline(self, mock_assess):
        mock_assess.return_value = self.match_result()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        application = response.data["content"][0]

        self.assertEqual(application["policyId"], self.policy.id)
        self.assertEqual(application["applicationEnd"], "2026-12-31")
        self.assertEqual(application["matchLevel"], "HIGH")
        self.assertEqual(application["matchReason"], "주거 상황과 잘 맞아요.")

    @patch("home.views.assess_policy_matches")
    def test_application_list_reuses_cached_match(self, mock_assess):
        mock_assess.return_value = self.match_result()

        self.client.get(self.url)
        self.client.get(self.url)

        self.assertEqual(mock_assess.call_count, 1)

    @patch("home.views.assess_policy_matches")
    def test_incomplete_profile_gets_null_match(self, mock_assess):
        User.objects.filter(id=self.user.id).update(profile_completed=False)

        application = self.client.get(self.url).data["content"][0]

        self.assertIsNone(application["matchLevel"])
        self.assertIsNone(application["matchReason"])
        # 마감일은 매칭과 무관하게 항상 내려간다.
        self.assertEqual(application["applicationEnd"], "2026-12-31")
        mock_assess.assert_not_called()

    @patch("home.views.assess_policy_matches")
    def test_ai_failure_still_returns_application_list(self, mock_assess):
        mock_assess.side_effect = GeminiRequestError("temporary failure")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        application = response.data["content"][0]

        self.assertEqual(application["policyId"], self.policy.id)
        self.assertIsNone(application["matchLevel"])

    @patch("home.views.assess_policy_matches")
    def test_policy_without_deadline_returns_null(self, mock_assess):
        mock_assess.return_value = PolicyMatchAssessmentResult(matches=[])
        Policy.objects.filter(id=self.policy.id).update(application_end=None)

        application = self.client.get(self.url).data["content"][0]

        self.assertIsNone(application["applicationEnd"])
