from django.contrib import admin

from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "organization", "application_end", "created_at"]
    list_filter = ["category"]
    search_fields = ["title", "summary"]