import threading
from typing import Any, Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from djoser.views import TokenCreateView
from djoser.views import User
from loguru import logger
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .emails import send_otp_email, send_password_reset_email
from .utils import generate_otp

User = get_user_model()


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: Optional[str] = None
) -> None:
    access_token_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    cookie_settings = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": access_token_lifetime,
    }
    response.set_cookie("access", access_token, **cookie_settings)

    if refresh_token:
        refresh_token_lifetime = settings.SIMPLE_JWT[
            "REFRESH_TOKEN_LIFETIME"
        ].total_seconds()
        refresh_cookie_settings = cookie_settings.copy()
        refresh_cookie_settings["max_age"] = refresh_token_lifetime
        response.set_cookie("refresh", refresh_token, **refresh_cookie_settings)

    logged_in_cookie_settings = cookie_settings.copy()
    logged_in_cookie_settings["httponly"] = False
    response.set_cookie("logged_in", "true", **logged_in_cookie_settings)


class CustomTokenCreateView(TokenCreateView):
    def _action(self, serializer):
        user = serializer.user
        if user.is_locked_out:
            return Response(
                {
                    "error": f"Account is locked due to multiple failed login attempts. Please "
                    f"try again after {settings.LOCKOUT_DURATION.total_seconds() / 60} minutes. ",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        user.reset_failed_login_attempts()

        otp = generate_otp()
        user.set_otp(otp)
        send_otp_email(user.email, otp)

        logger.info(f"OTP sent for login to user: {user.email}")

        return Response(
            {
                "success": "OTP sent to your email",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            email = request.data.get("email")
            user = User.objects.filter(email=email).first()
            if user:
                user.handle_failed_login_attempts()
                failed_attempts = user.failed_login_attempts
                logger.error(
                    f"Failed login attempts: {failed_attempts}  for user: {email}"
                )
                if failed_attempts >= settings.LOGIN_ATTEMPTS:
                    return Response(
                        {
                            "error": f"You have exceeded the maximum number of login attempts. "
                            f"Your account has been locked for "
                            f"{settings.LOCKOUT_DURATION.total_seconds() / 60} minutes. "
                            f"An email has been sent to you with further instructions",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                logger.error(f"Failed login attempt for non-existent user: {email}")

            return Response(
                {"error": "Your Login Credentials are not correct"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._action(serializer)


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        refresh_token = request.COOKIES.get("refresh")

        if refresh_token:
            request.data["refresh"] = refresh_token

        refresh_res = super().post(request, *args, **kwargs)

        if refresh_res.status_code == status.HTTP_200_OK:
            access_token = refresh_res.data.get("access")
            refresh_token = refresh_res.data.get("refresh")

            if access_token and refresh_token:
                set_auth_cookies(
                    refresh_res,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )

                refresh_res.data.pop("access", None)
                refresh_res.data.pop("refresh", None)

                refresh_res.data["message"] = "Access tokens refreshed successfully."

            else:
                refresh_res.data["message"] = (
                    "Access or refresh token not found in refresh response data"
                )
                logger.error(
                    "Access or refresh token not found in refresh response data"
                )

        return refresh_res


class OTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        otp = request.data.get("otp")

        if not otp:
            return Response(
                {"error": "OTP is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(otp=otp, otp_expiry_time__gt=timezone.now()).first()

        if not user:
            return Response(
                {"error": "Invalid or expired OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_locked_out:
            return Response(
                {
                    "error": f"Account is locked due to multiple failed login attempts. "
                    f"Please try again after "
                    f"{settings.LOCKOUT_DURATION.total_seconds() / 60} minutes "
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.verify_otp(otp)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "success": "Login successful. Now add your profile information, "
                "so that we can create an account for you"
            },
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, access_token, refresh_token)
        logger.info(f"Successful login with OTP: {user.email}")
        return response


class LogoutAPIView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        response.delete_cookie("logged_in")
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            token_generator = PasswordResetTokenGenerator()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            threading.Thread(
                target=send_password_reset_email, args=(email, reset_url), daemon=True
            ).start()
            logger.info(f"Password reset email queued for: {email}")

        return Response(
            {"detail": "If an account with that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password", "")

        if not all([uid, token, new_password]):
            return Response({"error": "uid, token, and new_password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_pk)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({"error": "This reset link has expired or is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info(f"Password reset successful for: {user.email}")
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)
