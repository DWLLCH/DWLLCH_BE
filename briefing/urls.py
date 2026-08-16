from django.urls import path

from . import views

urlpatterns = [
    path("briefings", views.briefing_list, name="briefing-list"),
]