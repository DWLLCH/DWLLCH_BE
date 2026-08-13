from b2g.exceptions import (
    B2GLicenseRequiredException,
    B2GPermissionDeniedException,
)
from b2g.models import OrganizationMembership


class IsOrganizationAdmin:
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
            raise B2GPermissionDeniedException()

        if not membership.organization.license_active:
            raise B2GLicenseRequiredException()

        request.organization_membership = membership
        request.organization = membership.organization
        return True