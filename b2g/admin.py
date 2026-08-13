from django.contrib import admin

from b2g.models import (
    ConsultRequest,
    Organization,
    OrganizationMembership,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "license_active",
        "created_at",
    )
    list_filter = ("license_active",)
    search_fields = ("name",)


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "user",
        "is_admin",
        "is_active",
    )
    list_filter = (
        "organization",
        "is_admin",
        "is_active",
    )


@admin.register(ConsultRequest)
class ConsultRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "requester",
        "urgency_level",
        "status",
        "risk_type",
        "received_at",
    )
    list_filter = (
        "organization",
        "urgency_level",
        "status",
        "risk_type",
    )
    search_fields = (
        "summary",
        "requester__email",
    )