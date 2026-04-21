import secrets

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone


def _split_emails(value):
    if not value:
        return []
    return [email.strip() for email in str(value).replace(";", ",").split(",") if email.strip()]


def _send_message(connection, subject, text_body, html_body, recipients, from_email):
    if not recipients:
        return False, "Khong co nguoi nhan."

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients,
            connection=connection,
        )
        if html_body:
            message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _send_sandbox_copy(subject, text_body, html_body, recipients):
    host = (getattr(settings, "MAILTRAP_SANDBOX_HOST", "") or "").strip()
    user = (getattr(settings, "MAILTRAP_SANDBOX_USER", "") or "").strip()
    password = (getattr(settings, "MAILTRAP_SANDBOX_PASSWORD", "") or "").strip()
    if not host or not user or not password or not recipients:
        return False, "Chua cau hinh sandbox."

    sandbox_recipients = list(dict.fromkeys(recipients + _split_emails(getattr(settings, "MAILTRAP_SANDBOX_TO_EMAIL", ""))))
    from_email = (getattr(settings, "MAILTRAP_SANDBOX_FROM_EMAIL", "") or "no-reply@mailtrap.local").strip()

    connection = mail.get_connection(
        host=host,
        port=getattr(settings, "MAILTRAP_SANDBOX_PORT", 587),
        username=user,
        password=password,
        use_tls=True,
    )
    return _send_message(connection, subject, text_body, html_body, sandbox_recipients, from_email)


def _send_live_email(subject, text_body, html_body, recipients):
    host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
    password = (getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip()
    user = (getattr(settings, "EMAIL_HOST_USER", "") or "api").strip()
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "no-reply@demomailtrap.co").strip()

    if not host or not password:
        return False, "Chua cau hinh SMTP live (MAILTRAP_PASSWORD)."

    connection = mail.get_connection(
        host=host,
        port=getattr(settings, "EMAIL_PORT", 587),
        username=user,
        password=password,
        use_tls=getattr(settings, "EMAIL_USE_TLS", True),
    )
    return _send_message(connection, subject, text_body, html_body, recipients, from_email)


def _delivery_result(live_ok, live_error, sandbox_ok, sandbox_error):
    return {
        "ok": live_ok or sandbox_ok,
        "live_sent": live_ok,
        "live_error": live_error,
        "sandbox_sent": sandbox_ok,
        "sandbox_error": sandbox_error,
    }


def _build_verify_url(request, parking_user):
    token = secrets.token_urlsafe(32)
    parking_user.email_verification_token = token
    parking_user.email_verification_sent_at = timezone.now()
    parking_user.email_verified = False
    parking_user.save(
        update_fields=[
            "email_verification_token",
            "email_verification_sent_at",
            "email_verified",
        ]
    )
    return request.build_absolute_uri(
        reverse("parking_user_verify_email", args=[parking_user.id, token])
    )


def _send_dual_delivery_email(subject, text_body, html_body, recipient_email):
    recipients = [recipient_email.strip()]
    live_ok, live_error = _send_live_email(subject, text_body, html_body, recipients)
    sandbox_ok, sandbox_error = _send_sandbox_copy(subject, text_body, html_body, recipients)
    return _delivery_result(live_ok, live_error, sandbox_ok, sandbox_error)


def send_parking_user_verification_email(request, parking_user, *, source_label="manager"):
    email_value = (parking_user.email or "").strip().lower()
    if not email_value:
        return {"ok": True, "live_sent": False, "sandbox_sent": False, "skipped": True}

    verify_url = _build_verify_url(request, parking_user)
    context = {
        "parking_user": parking_user,
        "source_label": source_label,
        "verify_url": verify_url,
    }

    subject = render_to_string(
        "parking/email/parking_user_registered_subject.txt",
        context,
    ).strip()
    text_body = render_to_string(
        "parking/email/parking_user_registered.txt",
        context,
    )
    html_body = render_to_string(
        "parking/email/parking_user_registered.html",
        context,
    )
    return _send_dual_delivery_email(subject, text_body, html_body, email_value)


def send_registration_request_received_email(registration):
    email_value = (registration.email or "").strip().lower()
    if not email_value:
        return {"ok": True, "live_sent": False, "sandbox_sent": False, "skipped": True}

    context = {"registration": registration}
    subject = render_to_string(
        "parking/email/registration_received_subject.txt",
        context,
    ).strip()
    text_body = render_to_string(
        "parking/email/registration_received.txt",
        context,
    )
    html_body = render_to_string(
        "parking/email/registration_received.html",
        context,
    )
    return _send_dual_delivery_email(subject, text_body, html_body, email_value)


def send_otp_email(email, otp_code):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[OTP] {email} → {otp_code}")

    subject = "Mã xác nhận đăng ký tài khoản Parking GIS"
    text_body = (
        f"Mã OTP của bạn là: {otp_code}\n"
        f"Mã có hiệu lực trong 10 phút. Không chia sẻ mã này cho người khác."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;border:1px solid #e2e8f0;border-radius:16px;">
        <h2 style="color:#0f172a;margin-bottom:8px;">Xác nhận đăng ký</h2>
        <p style="color:#475569;">Nhập mã sau để hoàn tất đăng ký tài khoản:</p>
        <div style="font-size:42px;font-weight:800;letter-spacing:10px;color:#2563eb;text-align:center;padding:24px 0;">
            {otp_code}
        </div>
        <p style="color:#94a3b8;font-size:13px;text-align:center;">Mã có hiệu lực trong <strong>10 phút</strong>. Không chia sẻ mã này cho người khác.</p>
    </div>
    """
    result = _send_dual_delivery_email(subject, text_body, html_body, email.strip().lower())
    if not result.get("ok"):
        logger.warning(f"[OTP] Gửi email thất bại cho {email}: {result}")
    return result
