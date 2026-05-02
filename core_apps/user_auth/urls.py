from django.urls import path

from .views import (
    CustomTokenCreateView,
    CustomTokenRefreshView,
    LogoutAPIView,
    OTPVerifyView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("login/", CustomTokenCreateView.as_view(), name="login"),
    path("verify-otp/", OTPVerifyView.as_view(), name="verify_otp"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("forgot-password/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("forgot-password/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
