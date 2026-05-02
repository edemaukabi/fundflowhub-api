from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from loguru import logger


def send_otp_email(email, otp):
    subject = _("Your OTP code for Login")
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    context = {
        "otp": otp,
        "expiry_time": settings.OTP_EXPIRATION,
        "site_name": settings.SITE_NAME,
    }
    html_email = render_to_string("emails/otp_email.html", context)
    plain_email = strip_tags(html_email)
    email = EmailMultiAlternatives(subject, plain_email, from_email, recipient_list)
    email.attach_alternative(html_email, "text/html")
    try:
        email.send()
        logger.info(f"OTP email sent successfully to: {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: Error: {str(e)}")


def send_password_reset_email(email, reset_url):
    subject = _("Reset your FundFlowHub password")
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    html_email = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f6fa;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 2px 12px rgba(0,0,0,0.06);">
    <h2 style="color:#1B2F5B;margin:0 0 8px;">Reset your password</h2>
    <p style="color:#555;margin:0 0 28px;line-height:1.6;">
      We received a request to reset your FundFlowHub password.
      Click the button below to choose a new one. This link expires in 1 hour.
    </p>
    <a href="{reset_url}" style="display:inline-block;background:#00BFA5;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:0.95rem;">
      Reset password
    </a>
    <p style="margin-top:28px;color:#999;font-size:0.85rem;line-height:1.6;">
      If you didn't request this, you can safely ignore this email — your password won't change.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:28px 0 16px;">
    <p style="color:#ccc;font-size:0.8rem;text-align:center;margin:0;">FundFlowHub — Secure Banking</p>
  </div>
</body>
</html>"""
    plain_email = strip_tags(html_email)
    msg = EmailMultiAlternatives(subject, plain_email, from_email, recipient_list)
    msg.attach_alternative(html_email, "text/html")
    try:
        msg.send()
        logger.info(f"Password reset email sent to: {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")


def send_account_locked_email(self):
    subject = _("Your account has been locked")
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [self.email]
    context = {
        "user": self,
        "lockout_duration": int(settings.LOCKOUT_DURATION.total_seconds() // 60),
        "site_name": settings.SITE_NAME,
    }
    html_email = render_to_string("emails/account_locked.html", context)
    plain_email = strip_tags(html_email)
    email = EmailMultiAlternatives(subject, plain_email, from_email, recipient_list)
    email.attach_alternative(html_email, "text/html")
    try:
        email.send()
        logger.info(f"Account locked email sent to : {self.email}")
    except Exception as e:
        logger.error(
            f"Failed to send account locked email to {self.email}: Error: {str(e)}"
        )
