from rest_framework.permissions import BasePermission

from b2g.models import OrganizationMembership


class IsOrganizationAdmin(BasePermission):
    message = "전담기관 관리자 권한이 필요합니다."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization_id = request.headers.get("X-Organization-ID")
        if not organization_id:
            self.message = "조직 식별자가 필요합니다. X-Organization-ID 헤더를 포함해주세요."
            return False

        try:
            organization_id = int(organization_id)
        except (ValueError, TypeError):
            self.message = "유효하지 않은 조직 식별자입니다."
            return False

        membership = (
            OrganizationMembership.objects
            .select_related("organization")
            .filter(
                organization_id=organization_id,
                user=request.user,
                is_admin=True,
                is_active=True,
            )
            .first()
        )

        if membership is None:
            self.message = "해당 조직의 활성 관리자 권한이 없습니다."
            return False

        request.organization = membership.organization
        return True