from unittest.mock import patch
from datetime import date, timedelta
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from home.models import Policy, PolicyScrap
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policy = response.data["content"][0]

        self.assertEqual(policy["matchLevel"], "HIGH")
        self.assertEqual(policy["matchReason"], "현재 주거 상황과 잘 맞아요.")

    def test_policy_list_guest_match_is_null(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policy = response.data["content"][0]

        self.assertIsNone(policy["matchLevel"])
        self.assertIsNone(policy["matchReason"])

    @patch("home.views.assess_policy_matches")
    def test_policy_list_ai_failure_still_success(self, mock_assess):
        self.authenticate()

        mock_assess.side_effect = GeminiRequestError()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policy = response.data["content"][0]

        self.assertIsNone(policy["matchLevel"])
        self.assertIsNone(policy["matchReason"])

    @patch("home.views.assess_policy_matches")
    def test_policy_list_profile_incomplete_skips_ai(self, mock_assess):
        self.user.profile_completed = False
        self.user.save(update_fields=["profile_completed"])

        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_assess.assert_not_called()

        policy = response.data["content"][0]

        self.assertIsNone(policy["matchLevel"])
        self.assertIsNone(policy["matchReason"])

    def test_policy_list_includes_updated_at(self):
        response = self.client.get("/policies")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policy = response.data["content"][0]

        self.assertIn("updatedAt", policy)


    def test_policy_list_sort_by_updated_at(self):
        older_policy = Policy.objects.create(
            title="이전 수정 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
        )

        newer_policy = Policy.objects.create(
            title="최근 수정 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
        )

        now = timezone.now()

        Policy.objects.filter(id=older_policy.id).update(updated_at=now - timedelta(days=1))

        Policy.objects.filter(id=newer_policy.id).update(updated_at=now)

        response = self.client.get("/policies?sort=updatedAt")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policies = response.data["content"]

        ids = [
            policy["id"]
            for policy in policies
            if policy["id"] in [
                older_policy.id,
                newer_policy.id,
            ]
        ]

        self.assertEqual(ids, [newer_policy.id, older_policy.id])


    def test_policy_list_sort_by_application_end(self):
        later_policy = Policy.objects.create(
            title="마감 늦은 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            application_end=date.today() + timedelta(days=10),
        )

        sooner_policy = Policy.objects.create(
            title="마감 빠른 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            application_end=date.today() + timedelta(days=3),
        )

        response = self.client.get("/policies?sort=applicationEnd")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policies = response.data["content"]

        ids = [
            policy["id"]
            for policy in policies
            if policy["id"] in [
                later_policy.id,
                sooner_policy.id,
            ]
        ]

        self.assertEqual(ids, [sooner_policy.id, later_policy.id])


    def test_policy_list_default_sort_is_updated_at(self):
        older_policy = Policy.objects.create(
            title="기본 정렬 이전 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
        )

        newer_policy = Policy.objects.create(
            title="기본 정렬 최신 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
        )

        now = timezone.now()

        Policy.objects.filter(id=older_policy.id).update(updated_at=now - timedelta(days=1))

        Policy.objects.filter(id=newer_policy.id).update(updated_at=now)

        response = self.client.get("/policies")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policies = response.data["content"]

        ids = [
            policy["id"]
            for policy in policies
            if policy["id"] in [
                older_policy.id,
                newer_policy.id,
            ]
        ]

        self.assertEqual(ids, [newer_policy.id, older_policy.id])


    def test_policy_list_invalid_sort_fail(self):
        response = self.client.get("/policies?sort=invalid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class PolicyScrapTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="scrap@example.com",
            username="scrapuser",
            password="Test1234!",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="Test1234!",
        )

        self.policy = Policy.objects.create(
            title="청년 주거 지원",
            summary="주거 지원 정책",
            content="정책 내용",
            eligibility="자립준비청년",
            application_method="온라인 신청",
            required_documents="신분증",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="테스트 기관",
        )

        self.other_policy = Policy.objects.create(
            title="취업 지원",
            summary="취업 지원 정책",
            content="정책 내용",
            eligibility="자립준비청년",
            application_method="온라인 신청",
            required_documents="신분증",
            category=Policy.Category.EMPLOYMENT,
            target_condition="취업",
            organization="테스트 기관",
        )

        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_policy_scrap_create_success(self):
        response = self.client.post(f"/policies/{self.policy.id}/scrap")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            PolicyScrap.objects.filter(
                user=self.user,
                policy=self.policy,
            ).exists()
        )

        self.assertEqual(response.data["data"]["policyId"], self.policy.id)
        self.assertEqual(response.data["data"]["policyTitle"], self.policy.title)
        self.assertEqual(response.data["data"]["category"], self.policy.category)
        self.assertIn("applicationEnd", response.data["data"])

    def test_policy_scrap_duplicate_fail(self):
        PolicyScrap.objects.create(user=self.user, policy=self.policy)

        response = self.client.post(f"/policies/{self.policy.id}/scrap")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            PolicyScrap.objects.filter(
                user=self.user,
                policy=self.policy,
            ).count(),
            1,
        )

    def test_policy_scrap_delete_success(self):
        PolicyScrap.objects.create(user=self.user, policy=self.policy)

        response = self.client.delete(f"/policies/{self.policy.id}/scrap")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(
            PolicyScrap.objects.filter(
                user=self.user,
                policy=self.policy,
            ).exists()
        )

    def test_policy_scrap_delete_not_found(self):
        response = self.client.delete(f"/policies/{self.policy.id}/scrap")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_policy_scrap_list_success(self):
        PolicyScrap.objects.create(user=self.user, policy=self.policy)
        PolicyScrap.objects.create(user=self.user, policy=self.other_policy)

        response = self.client.get("/policies/scraps")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["content"]), 2)

        first = response.data["content"][0]

        self.assertIn("policyId", first)
        self.assertIn("policyTitle", first)
        self.assertIn("category", first)
        self.assertIn("applicationEnd", first)
        self.assertIn("createdAt", first)

    def test_policy_scrap_list_excludes_other_user(self):
        PolicyScrap.objects.create(user=self.user, policy=self.policy)

        PolicyScrap.objects.create(user=self.other_user, policy=self.other_policy)

        response = self.client.get("/policies/scraps")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policy_ids = [
            item["policyId"]
            for item in response.data["content"]
        ]

        self.assertIn(self.policy.id, policy_ids)
        self.assertNotIn(self.other_policy.id,policy_ids)

    def test_policy_scrap_unauthenticated_fail(self):
        self.client.credentials()

        response = self.client.post(f"/policies/{self.policy.id}/scrap")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_policy_scrap_list_unauthenticated_fail(self):
        self.client.credentials()

        response = self.client.get("/policies/scraps")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


def test_policy_required_documents_structure(self):
    self.policy.required_document_items = [
        {
            "label": "주민등록등본",
            "issueMethod": "정부24 발급",
            "linkUrl": "https://www.gov.kr",
        }
    ]
    self.policy.save()

    response = self.client.get(
        f"/policies/{self.policy.id}"
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
    )

    document = response.data["data"]["requiredDocuments"][0]

    self.assertEqual(
        document["label"],
        "주민등록등본",
    )
    self.assertEqual(
        document["issueMethod"],
        "정부24 발급",
    )
    self.assertEqual(
        document["linkUrl"],
        "https://www.gov.kr",
    )