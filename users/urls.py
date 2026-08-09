from django.urls import path

from .views import (
    SignupView, 
    EmailCheckView, 
    UsernameCheckView, 
    LoginView, 
    LogoutView, 
    ReissueView,
    PasswordChangeView,
    AccountDeleteView,
    AuthTestView,
)

urlpatterns = [
    path("auth/signup", SignupView.as_view(), name="signup"),
    path("auth/signup/email/check", EmailCheckView.as_view(), name="email-check",),
    path("auth/signup/username/check", UsernameCheckView.as_view(), name="username-check",),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/reissue", ReissueView.as_view(), name="reissue"),
    path("auth/password", PasswordChangeView.as_view(), name="password-change"),
    path("auth/account", AccountDeleteView.as_view(), name="account-delete"),
]