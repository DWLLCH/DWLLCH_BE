from django.urls import path

from . import views

urlpatterns = [
    path("mypage/status", views.mypage_status, name="mypage-status"),
    path("mypage/profile", views.mypage_profile, name="mypage-profile"),
    path("mypage/applications", views.application_list, name="application-list"),
    path("mypage/applications/<int:application_id>", views.application_delete, name="application-delete"),
    path("mypage/applications/<int:application_id>/status", views.application_status_update, name="application-status-update"),
]