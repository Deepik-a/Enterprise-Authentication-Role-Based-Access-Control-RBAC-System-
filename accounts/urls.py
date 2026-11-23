from django.urls import path

from .views import (
    ActivateAccountView, ChangePasswordView, ForgotPasswordView, LoginView, LogoutAllView,
    LogoutView, MeView, RefreshView, RegisterView, ResendActivationView, ResendOTPView,
    ResetPasswordView, VerifyOTPView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("resend-otp/", ResendOTPView.as_view()),
    path("activate/", ActivateAccountView.as_view()),
    path("resend-activation/", ResendActivationView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", RefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("logout-all/", LogoutAllView.as_view()),
    path("me/", MeView.as_view()),
    path("forgot-password/", ForgotPasswordView.as_view()),
    path("reset-password/", ResetPasswordView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
]
