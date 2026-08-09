from django.urls import path

from .views import SignupView, EmailCheckView, UsernameCheckView, LoginView, ReissueView

urlpatterns = [
    path("auth/signup", SignupView.as_view()),
    path("auth/signup/email/check", EmailCheckView.as_view(), name="email-check",),
    path("auth/signup/username/check", UsernameCheckView.as_view(), name="username-check",),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/logout", LoginView.as_view(), name="logout"),
    path("auth/reissue", ReissueView.as_view(), name="reissue"),
]