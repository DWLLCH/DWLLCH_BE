from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from home.models import Policy
from home.services import (
    PolicyMatchAssessment,
    PolicyMatchAssessmentResult,
    GeminiRequestError,
)


class PolicyListMatchTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="policy@example.com",
            username="policyuser",
            password="Test1234!",
            profile_completed=True,
            sido="서울특별시",
            sigungu="동대문구",
            protection_status=User.ProtectionStatus.ENDED,
            living_status=[User.LivingStatus.JOB_SEEKING],
            needed_help=[User.NeededHelp.HOUSING],
            housing_situation=User.HousingSituation.BURDEN,
            income_type=User.IncomeType.NONE,
        )

        self.policy = Policy.objects.create(
            title="청년 주거 지원",
            summary="주거비 지원 정책입니다.",
            content="정책 내용",
            eligibility="자립준비청년 대상",
            application_method="온라인 신청",
            required_documents="신분증",
            category=Policy.Category.HOUSING,
            target_condition="주거 월세 자립준비청년",
            organization="테스트 기관",
        )

        self.url = "/policies"

    def authenticate(self):
        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    @patch("home.views.assess_policy_matches")
    def test_policy_list_with_match_level(self, mock_assess):
        self.authenticate()

        mock_assess.return_value = PolicyMatchAssessmentResult(
            matches=[
                PolicyMatchAssessment(
                    policy_id=self.policy.id,
                    match_level="HIGH",
                    match_reason="현재 주거 상황과 잘 맞아요.",
                )
            ]
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        policy = response.data["content"][0]

        self.assertEqual(
            policy["matchLevel"],
            "HIGH",
        )
        self.assertEqual(
            policy["matchReason"],
            "현재 주거 상황과 잘 맞아요.",
        )

    def test_policy_list_guest_match_is_null(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        policy = response.data["content"][0]

        self.assertIsNone(
            policy["matchLevel"]
        )
        self.assertIsNone(
            policy["matchReason"]
        )

    @patch("home.views.assess_policy_matches")
    def test_policy_list_ai_failure_still_success(
        self,
        mock_assess,
    ):
        self.authenticate()

        mock_assess.side_effect = GeminiRequestError()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        policy = response.data["content"][0]

        self.assertIsNone(
            policy["matchLevel"]
        )
        self.assertIsNone(
            policy["matchReason"]
        )

    @patch("home.views.assess_policy_matches")
    def test_policy_list_profile_incomplete_skips_ai(
        self,
        mock_assess,
    ):
        self.user.profile_completed = False
        self.user.save(
            update_fields=["profile_completed"]
        )

        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_assess.assert_not_called()

        policy = response.data["content"][0]

        self.assertIsNone(
            policy["matchLevel"]
        )
        self.assertIsNone(
            policy["matchReason"]
        )