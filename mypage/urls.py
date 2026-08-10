from django.urls import path

from . import views

urlpatterns = [
    path("mypage/status", views.mypage_status, name="mypage-status"),
    path("mypage/profile", views.mypage_profile, name="mypage-profile"),
]