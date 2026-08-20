from datetime import date
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from briefing.models import Briefing, BriefingSummaryCache
from users.models import User


class BriefingCardVisualTest(APITestCase):
    """브리핑 카드 색상/아이콘이 목록과 상세 모두에 내려가는지."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="briefing@example.com",
            username="briefinguser",
            password="Test1234!",
            birth_date=date(2000, 1, 1),
            living_status=[User.LivingStatus.JOB_SEEKING],
            needed_help=[User.NeededHelp.HOUSING],
            housing_situation=User.HousingSituation.BURDEN,
        )

        self.briefing = Briefing.objects.create(
            category=Briefing.Category.HOUSING,
            title="전세 계약 전 확인할 것",
            card_summary="계약 전 확인 사항을 알려드려요",
            content="## 1. 등기부등본 확인",
            source_facts=["등기부등본을 확인하세요"],
            color=Briefing.Color.BLUE,
            icon=Briefing.Icon.HOME,
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

        # 상세 조회는 요약 생성을 위해 AI 를 부르므로 캐시를 미리 넣어 호출을 막는다.
        BriefingSummaryCache.objects.create(
            briefing=self.briefing,
            profile_signature=self.profile_signature(),
            generated_summary={"bullets": ["요약 항목"]},
        )

    def profile_signature(self):
        from briefing.models import compute_profile_signature

        return compute_profile_signature(self.user)

    @patch("briefing.views.generate_briefing_summary")
    def test_detail_includes_color_and_icon(self, generate_summary):
        response = self.client.get(f"/briefings/{self.briefing.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(data["color"], "blue")
        self.assertEqual(data["icon"], "home")
        generate_summary.assert_not_called()

    @patch("briefing.views.generate_briefing_summary")
    def test_list_and_detail_return_the_same_visual(self, generate_summary):
        list_response = self.client.get("/briefings")
        detail_response = self.client.get(f"/briefings/{self.briefing.id}")

        listed = next(
            item
            for item in list_response.data["content"]
            if item["id"] == self.briefing.id
        )
        detail = detail_response.data["data"]

        self.assertEqual(
            (listed["color"], listed["icon"]),
            (detail["color"], detail["icon"]),
        )

    @patch("briefing.views.generate_briefing_summary")
    def test_detail_keeps_existing_fields(self, generate_summary):
        """색상/아이콘을 추가하면서 기존 필드가 빠지지 않았는지."""
        response = self.client.get(f"/briefings/{self.briefing.id}")

        self.assertEqual(
            set(response.data["data"]),
            {
                "id",
                "category",
                "title",
                "cardSummary",
                "content",
                "thumbnail",
                "color",
                "icon",
                "keySummary",
            },
        )
        self.assertEqual(response.data["data"]["keySummary"], ["요약 항목"])
