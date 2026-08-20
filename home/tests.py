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

        # 시드 데이터에 밀려 첫 페이지에서 빠지지 않도록 이 테스트가 만든 정책만 조회한다.
        response = self.client.get(
            "/policies",
            {"sort": "updatedAt", "keyword": "수정 정책"},
        )

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

        always_open_policy = Policy.objects.create(
            title="마감 없는 상시모집 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            application_end=None,
        )

        # 시드 데이터에 밀려 첫 페이지에서 빠지지 않도록 이 테스트가 만든 정책만 조회한다.
        response = self.client.get(
            "/policies",
            {"sort": "applicationEnd", "keyword": "마감"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        policies = response.data["content"]

        ids = [
            policy["id"]
            for policy in policies
            if policy["id"] in [
                later_policy.id,
                sooner_policy.id,
                always_open_policy.id,
            ]
        ]

        # 마감이 임박한 순서로 보여주는 정렬이므로 상시모집은 맨 뒤여야 한다.
        # NULL 을 앞에 두는 DB(SQLite)에서도 같은 순서가 나와야 한다.
        self.assertEqual(
            ids,
            [sooner_policy.id, later_policy.id, always_open_policy.id],
        )


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

        # 정렬 파라미터 없이(기본값) 조회하되, 시드 데이터에 밀리지 않도록 범위를 좁힌다.
        response = self.client.get("/policies", {"keyword": "기본 정렬"})

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


class PolicyGroupFilterTest(APITestCase):
    def setUp(self):
        self.url = "/policies"

        self.residential_under_18 = Policy.objects.create(
            title="아동양육시설 만 18세 미만 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            protection_types=[Policy.ProtectionType.RESIDENTIAL_CARE],
            age_ranges=[Policy.AgeRange.UNDER_18],
        )

        self.residential_and_group_home = Policy.objects.create(
            title="아동양육시설+공동생활가정 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
            protection_types=[
                Policy.ProtectionType.RESIDENTIAL_CARE,
                Policy.ProtectionType.GROUP_HOME,
            ],
        )

        self.income_only = Policy.objects.create(
            title="기초생활수급자 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.FINANCE,
            target_condition="금융",
            organization="기관",
            income_criteria=[Policy.IncomeCriteria.BASIC_LIVELIHOOD],
        )

        self.unrelated_policy = Policy.objects.create(
            title="필터 조건 없는 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.ETC,
            target_condition="기타",
            organization="기관",
        )

        # 보호유형과 소득기준 양쪽에 조건이 있어, 선택값과 어긋나면 확실히 제외되는 정책.
        # 조건이 비어 있는 정책은 "제한 없음"으로 보고 항상 매칭되므로,
        # 제외 동작을 검증하려면 이렇게 양쪽이 채워진 정책이 필요하다.
        self.foster_near_poor = Policy.objects.create(
            title="가정위탁 차상위 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.ETC,
            target_condition="기타",
            organization="기관",
            protection_types=[Policy.ProtectionType.FOSTER_CARE],
            income_criteria=[Policy.IncomeCriteria.NEAR_POOR],
        )

    def test_no_filter_returns_all_policies(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [policy["id"] for policy in response.data["content"]]

        self.assertIn(self.residential_under_18.id, ids)
        self.assertIn(self.unrelated_policy.id, ids)

    def test_single_value_filter_matches_policy(self):
        response = self.client.get(self.url, {"protectionType": "RESIDENTIAL_CARE"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [policy["id"] for policy in response.data["content"]]

        self.assertIn(self.residential_under_18.id, ids)
        self.assertIn(self.residential_and_group_home.id, ids)

        # 보호유형을 지정하지 않은 정책은 대상 제한이 없다는 뜻이라 함께 노출된다.
        self.assertIn(self.income_only.id, ids)
        self.assertIn(self.unrelated_policy.id, ids)

        # 다른 보호유형만 대상으로 하는 정책은 제외된다.
        self.assertNotIn(self.foster_near_poor.id, ids)

    def test_same_group_multi_select_is_and(self):
        response = self.client.get(
            self.url,
            {"protectionType": "RESIDENTIAL_CARE,GROUP_HOME"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [policy["id"] for policy in response.data["content"]]

        self.assertIn(self.residential_and_group_home.id, ids)
        self.assertNotIn(self.residential_under_18.id, ids)

    def test_cross_group_filter_is_or(self):
        response = self.client.get(
            self.url,
            {
                "protectionType": "RESIDENTIAL_CARE,GROUP_HOME",
                "incomeCriteria": "BASIC_LIVELIHOOD",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [policy["id"] for policy in response.data["content"]]

        # 보호유형 그룹을 충족하거나, 소득 그룹을 충족하면 노출된다.
        self.assertIn(self.residential_and_group_home.id, ids)
        self.assertIn(self.income_only.id, ids)

        # 보호유형은 어긋나지만 소득 조건이 없어 소득 그룹에서는 제한이 없다.
        self.assertIn(self.residential_under_18.id, ids)
        self.assertIn(self.unrelated_policy.id, ids)

        # 두 그룹 모두 어긋나는 정책만 빠진다.
        self.assertNotIn(self.foster_near_poor.id, ids)

    def test_filter_combines_with_category(self):
        response = self.client.get(
            self.url,
            {"protectionType": "RESIDENTIAL_CARE", "category": "FINANCE"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = [policy["id"] for policy in response.data["content"]]

        # FINANCE 이면서 보호유형 제한이 없으므로 남는다.
        self.assertIn(self.income_only.id, ids)

        # 카테고리가 달라 보호유형과 무관하게 빠진다.
        self.assertNotIn(self.residential_under_18.id, ids)
        self.assertNotIn(self.residential_and_group_home.id, ids)
        self.assertNotIn(self.unrelated_policy.id, ids)
        self.assertNotIn(self.foster_near_poor.id, ids)

    def test_invalid_protection_type_fails(self):
        response = self.client.get(self.url, {"protectionType": "INVALID"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_age_range_fails(self):
        response = self.client.get(self.url, {"ageRange": "INVALID"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_income_criteria_fails(self):
        response = self.client.get(self.url, {"incomeCriteria": "INVALID"})

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


class PolicyScrapMatchTest(APITestCase):
    """스크랩 목록의 AI 예상 적합도(matchLevel/matchReason)."""

    def setUp(self):
        self.url = "/policies/scraps"

        self.user = User.objects.create_user(
            email="scrapmatch@example.com",
            username="scrapmatchuser",
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
            title="스크랩 매칭 대상 정책",
            summary="요약",
            content="내용",
            eligibility="자격",
            application_method="신청 방법",
            required_documents="서류",
            category=Policy.Category.HOUSING,
            target_condition="주거",
            organization="기관",
        )

        PolicyScrap.objects.create(user=self.user, policy=self.policy)

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
    def test_scrap_list_includes_match_fields(self, mock_assess):
        mock_assess.return_value = self.match_result()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scrap = response.data["content"][0]

        self.assertEqual(scrap["policyId"], self.policy.id)
        self.assertEqual(scrap["matchLevel"], "HIGH")
        self.assertEqual(scrap["matchReason"], "주거 상황과 잘 맞아요.")

    @patch("home.views.assess_policy_matches")
    def test_scrap_list_reuses_cached_match(self, mock_assess):
        """두 번째 조회는 정책 단위 캐시를 써서 AI 를 다시 부르지 않는다."""
        mock_assess.return_value = self.match_result()

        self.client.get(self.url)
        self.client.get(self.url)

        self.assertEqual(mock_assess.call_count, 1)

    @patch("home.views.assess_policy_matches")
    def test_incomplete_profile_gets_null_match(self, mock_assess):
        User.objects.filter(id=self.user.id).update(profile_completed=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scrap = response.data["content"][0]

        self.assertIsNone(scrap["matchLevel"])
        self.assertIsNone(scrap["matchReason"])
        mock_assess.assert_not_called()

    @patch("home.views.assess_policy_matches")
    def test_ai_failure_still_returns_scrap_list(self, mock_assess):
        """매칭 실패가 스크랩 목록 조회를 막지 않는다."""
        mock_assess.side_effect = GeminiRequestError("temporary failure")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scrap = response.data["content"][0]

        self.assertEqual(scrap["policyId"], self.policy.id)
        self.assertIsNone(scrap["matchLevel"])
        self.assertIsNone(scrap["matchReason"])

    def test_scrap_list_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
