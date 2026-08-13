from rest_framework.permissions import BasePermission

from b2g.models import OrganizationMembership


class IsOrganizationAdmin(BasePermission):
    message = "전담기관 관리자 권한이 필요합니다."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        membership = (
            OrganizationMembership.objects
            .select_related("organization")
            .filter(
                user=request.user,
                is_admin=True,
                is_active=True,
            )
            .first()
        )

        if membership is None:
            return False

        request.organization = membership.organization
        return True