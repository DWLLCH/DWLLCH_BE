from django.urls import path

from .views import SignupView, EmailCheckView

urlpatterns = [
    path("auth/signup", SignupView.as_view()),
    path("auth/signup/email/check", EmailCheckView.as_view(), name="email-check",),
]