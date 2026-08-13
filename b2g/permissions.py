from rest_framework.permissions import BasePermission

from b2g.models import OrganizationMembership


class IsOrganizationAdmin(BasePermission):
    message = "전담기관 관리자 권한이 필요합니다."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        organization_id = request.headers.get("X-Organization-ID")

        if not organization_id:
            self.message = "기관 정보가 필요합니다."
            return False

        try:
            organization_id = int(organization_id)
        except (TypeError, ValueError):
            self.message = "기관 정보가 올바르지 않습니다."
            return False

        try:
            membership = (
                OrganizationMembership.objects
                .select_related("organization")
                .get(
                    organization_id=organization_id,
                    user=request.user,
                    is_admin=True,
                    is_active=True,
                )
            )
        except OrganizationMembership.DoesNotExist:
            self.message = "해당 기관의 관리자 권한이 없습니다."
            return False

        request.organization = membership.organization
        return True