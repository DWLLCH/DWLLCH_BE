from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import RefreshToken

from b2g.models import (
    ConsultRequest,
    Organization,
    OrganizationMembership,
)


User = get_user_model()


class B2GDashboardAPITestCase(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="서울 청년지원기관",
            license_active=True,
        )
        self.other_organization = Organization.objects.create(
            name="부산 청년지원기관",
            license_active=True,
        )

        self.admin_user = self.create_user(
            username="organization_admin",
            email="admin@example.com",
        )
        self.requester = self.create_user(
            username="requester",
            email="requester@example.com",
        )
        self.other_requester = self.create_user(
            username="other_requester",
            email="other@example.com",
        )
        self.normal_user = self.create_user(
            username="normal_user",
            email="normal@example.com",
        )

        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.admin_user,
            is_admin=True,
            is_active=True,
        )

        self.high_request = ConsultRequest.objects.create(
            organization=self.organization,
            requester=self.requester,
            urgency_level=ConsultRequest.UrgencyLevel.HIGH,
            status=ConsultRequest.Status.RECEIVED,
            risk_type=ConsultRequest.RiskType.HOUSING_FRAUD,
            summary="전세사기 위험이 의심됩니다.",
            structured_report={
                "date": "2026-08-01",
                "amount": 5000000,
                "location": "서울특별시 관악구",
                "counterpart": "임대인",
                "situationSummary": "등기부등본을 확인하지 않았습니다.",
                "riskType": "전세사기 의심",
            },
            pre_interview=[
                {
                    "question": "등기부등본을 확인했나요?",
                    "answer": "아니요",
                }
            ],
            consent_scope=[
                "STRUCTURED_REPORT",
                "PRE_INTERVIEW",
            ],
            linkage_consented=True,
        )

        self.critical_request = ConsultRequest.objects.create(
            organization=self.organization,
            requester=self.requester,
            urgency_level=ConsultRequest.UrgencyLevel.CRITICAL,
            status=ConsultRequest.Status.RESOLVED,
            risk_type=ConsultRequest.RiskType.FINANCIAL_SCAM,
            summary="금융사기 피해 위험이 매우 높습니다.",
            structured_report={"amount": 10000000},
            pre_interview=[],
            consent_scope=["STRUCTURED_REPORT"],
            linkage_consented=True,
        )

        # 사용자가 연계에 동의하지 않은 요청
        self.not_consented_request = ConsultRequest.objects.create(
            organization=self.organization,
            requester=self.requester,
            urgency_level=ConsultRequest.UrgencyLevel.CRITICAL,
            status=ConsultRequest.Status.RECEIVED,
            risk_type=ConsultRequest.RiskType.OTHER,
            summary="동의하지 않은 요청",
            linkage_consented=False,
        )

        # 다른 기관의 요청
        self.other_organization_request = ConsultRequest.objects.create(
            organization=self.other_organization,
            requester=self.other_requester,
            urgency_level=ConsultRequest.UrgencyLevel.CRITICAL,
            status=ConsultRequest.Status.RECEIVED,
            risk_type=ConsultRequest.RiskType.HOUSING_FRAUD,
            summary="다른 기관의 요청",
            linkage_consented=True,
        )

        now = timezone.make_aware(
            datetime.combine(
                timezone.localdate(),
                time(hour=12),
            )
        )
        
        ConsultRequest.objects.filter(
            id=self.high_request.id
        ).update(
            received_at=now - timedelta(minutes=60),
            assigned_at=now - timedelta(minutes=30),
        )

        ConsultRequest.objects.filter(
            id=self.critical_request.id
        ).update(
            received_at=now - timedelta(minutes=120),
            assigned_at=now - timedelta(minutes=80),
            resolved_at=now,
        )

        self.client.force_authenticate(user=self.admin_user)
        self.client.credentials(
            HTTP_X_ORGANIZATION_ID=str(self.organization.id)
        )

    def create_user(self, username, email):
        return User.objects.create_user(
            username=username,
            email=email,
            password="TestPassword123!",
            birth_date=date(2000, 1, 1),
            protection_end_date=date(2025, 1, 1),
            sido="서울특별시",
            sigungu="관악구",
            protection_type=User.ProtectionType.RESIDENTIAL_CARE,
            housing_type=User.HousingType.JEONSE,
            housing_situation=User.HousingSituation.STABLE,
            living_status=[User.LivingStatus.NONE],
            income_type=User.IncomeType.NONE,
            support_received=[User.SupportType.NONE],
            needed_help=[User.NeededHelp.HOUSING],
        )

    def test_authentication_is_required(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/b2g/dashboard/requests")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertFalse(response.data["success"])
        self.assertEqual(
            response.data["code"],
            "AUTH_401_UNAUTHORIZED",
        )

    def test_non_admin_cannot_access_dashboard(self):
        self.client.force_authenticate(user=self.normal_user)

        response = self.client.get("/b2g/dashboard/requests")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            response.data["code"],
            "AUTH_403_FORBIDDEN",
        )

    def test_inactive_license_returns_402(self):
        self.organization.license_active = False
        self.organization.save(update_fields=["license_active"])

        response = self.client.get("/b2g/dashboard/requests")

        self.assertEqual(response.status_code, 402)
        self.assertEqual(
            response.data["code"],
            "B2G_402_LICENSE_REQUIRED",
        )

    def test_list_returns_only_consented_requests_from_same_organization(self):
        response = self.client.get("/b2g/dashboard/requests")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        data = response.data["data"]

        self.assertEqual(data["totalElements"], 2)
        self.assertEqual(len(data["content"]), 2)

        request_ids = {
            item["requestId"] for item in data["content"]
        }

        self.assertIn(self.high_request.id, request_ids)
        self.assertIn(self.critical_request.id, request_ids)
        self.assertNotIn(self.not_consented_request.id, request_ids)
        self.assertNotIn(
            self.other_organization_request.id,
            request_ids,
        )

    def test_list_orders_requests_by_urgency_descending(self):
        response = self.client.get(
            "/b2g/dashboard/requests?sort=urgencyLevel,desc"
        )

        content = response.data["data"]["content"]

        self.assertEqual(content[0]["urgencyLevel"], "CRITICAL")
        self.assertEqual(content[1]["urgencyLevel"], "HIGH")

    def test_list_filters_by_urgency_and_status(self):
        response = self.client.get(
            "/b2g/dashboard/requests"
            "?urgencyLevel=HIGH&status=RECEIVED"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.data["data"]["content"]

        self.assertEqual(len(content), 1)
        self.assertEqual(
            content[0]["requestId"],
            self.high_request.id,
        )

    def test_invalid_list_parameter_returns_400(self):
        response = self.client.get(
            "/b2g/dashboard/requests?urgencyLevel=INVALID"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["code"],
            "COMMON_400_INVALID_INPUT",
        )

    def test_detail_returns_consented_information(self):
        response = self.client.get(
            f"/b2g/dashboard/requests/{self.high_request.id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(data["requestId"], self.high_request.id)
        self.assertEqual(data["urgencyLevel"], "HIGH")
        self.assertEqual(
            data["structuredReport"]["amount"],
            5000000,
        )
        self.assertEqual(len(data["preInterview"]), 1)
        self.assertNotIn("email", data)
        self.assertNotIn("detailAddress", data)

    def test_detail_hides_information_outside_consent_scope(self):
        response = self.client.get(
            f"/b2g/dashboard/requests/{self.critical_request.id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]

        self.assertEqual(
            data["structuredReport"],
            {"amount": 10000000},
        )
        self.assertEqual(data["preInterview"], [])

    def test_other_organization_request_is_hidden(self):
        response = self.client.get(
            "/b2g/dashboard/requests/"
            f"{self.other_organization_request.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_stats_returns_organization_statistics(self):
        today = timezone.localdate()
        from_date = today - timedelta(days=7)

        response = self.client.get(
            "/b2g/dashboard/stats"
            f"?from={from_date.isoformat()}"
            f"&to={today.isoformat()}"
            "&groupBy=DAY"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["data"]
        summary = data["summary"]

        self.assertEqual(summary["totalRequests"], 2)
        self.assertEqual(summary["criticalRequests"], 1)
        self.assertEqual(summary["highRequests"], 1)
        self.assertEqual(summary["resolvedRequests"], 1)
        self.assertEqual(summary["averageResponseMinutes"], 35)
        self.assertEqual(len(data["trend"]), 1)

    def test_stats_rejects_invalid_period(self):
        response = self.client.get(
            "/b2g/dashboard/stats"
            "?from=2026-08-10"
            "&to=2026-08-01"
            "&groupBy=DAY"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["code"],
            "COMMON_400_INVALID_INPUT",
        )

    def test_stats_rejects_invalid_group_by(self):
        response = self.client.get(
            "/b2g/dashboard/stats?groupBy=YEAR"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_cannot_access_unassigned_organization(self):
        self.client.credentials(
            HTTP_X_ORGANIZATION_ID=str(
                self.other_organization.id
            )
        )

        response = self.client.get(
            "/b2g/dashboard/requests"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            response.data["code"],
            "AUTH_403_FORBIDDEN",
        )

    def test_organization_header_is_required(self):
        self.client.credentials()

        response = self.client.get("/b2g/dashboard/requests")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            response.data["code"],
            "AUTH_403_FORBIDDEN",
        )

    def test_my_organizations_returns_admin_memberships(self):
        inactive_organization = Organization.objects.create(
            name="비활성 관리자 기관",
            license_active=True,
        )
        non_admin_organization = Organization.objects.create(
            name="일반 구성원 기관",
            license_active=True,
        )
        OrganizationMembership.objects.create(
            organization=inactive_organization,
            user=self.admin_user,
            is_admin=True,
            is_active=False,
        )
        OrganizationMembership.objects.create(
            organization=non_admin_organization,
            user=self.admin_user,
            is_admin=False,
            is_active=True,
        )

        response = self.client.get("/b2g/organizations/me")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["organizations"],
            [
                {
                    "organizationId": self.organization.id,
                    "name": self.organization.name,
                    "licenseActive": True,
                }
            ],
        )


    def test_account_delete_with_retained_consult_request_returns_409(self):
        stored_token = RefreshToken.objects.create(
            user=self.requester,
            token="stored-refresh-token",
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.requester)
        self.client.credentials()

        response = self.client.delete(
            "/auth/account",
            {"password": "TestPassword123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["code"],
            "USER_409_RETAINED_DATA_EXISTS",
        )
        self.assertTrue(User.objects.filter(id=self.requester.id).exists())
        self.assertTrue(
            ConsultRequest.objects.filter(
                requester_id=self.requester.id
            ).exists()
        )
        self.assertTrue(
            RefreshToken.objects.filter(id=stored_token.id).exists()
        )


    def test_my_organizations_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.client.credentials()

        response = self.client.get("/b2g/organizations/me")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            response.data["code"],
            "AUTH_401_UNAUTHORIZED",
        )
