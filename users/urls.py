from django.urls import path

from .views import SignupView, EmailCheckView, UsernameCheckView

urlpatterns = [
    path("auth/signup", SignupView.as_view()),
    path("auth/signup/email/check", EmailCheckView.as_view(), name="email-check",),
    path("auth/signup/username/check", UsernameCheckView.as_view(), name="username-check",),
]