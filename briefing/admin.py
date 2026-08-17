from django.contrib import admin

from .models import Briefing


@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "created_at"]
    list_filter = ["category"]
    search_fields = ["title", "card_summary"]