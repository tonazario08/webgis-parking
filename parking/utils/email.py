import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone


def send_parking_user_verification_email(request, parking_user):
    email_value = (parking_user.email or "").strip()
    if not email_value:
        return True, None

    token = secrets.token_urlsafe(32)
    parking_user.email_verification_token = token
    parking_user.email_verification_sent_at = timezone.now()
    parking_user.email_verified = False
    parking_user.save(update_fields=[
        "email_verification_token",
        "email_verification_sent_at",
        "email_verified",
    ])

    verify_url = request.build_absolute_uri(
        reverse("parking_user_verify_email", args=[parking_user.id, token])
    )

    subject = "Xac thuc email - Parking Manager"
    text_body = (
        "Xin chao {name},\n\n"
        "Ban vua duoc dang ky gui xe tai he thong Parking Manager.\n"
        "Vui long nhan vao link ben duoi de xac thuc email:\n"
        "{url}\n\n"
        "Thong tin dang ky:\n"
        "- Bien so xe: {plate}\n"
        "- Bai do xe: {lot}\n\n"
        "Cam on!"
    ).format(
        name=parking_user.full_name,
        url=verify_url,
        plate=parking_user.license_plate,
        lot=parking_user.parking_lot.name,
    )

    html_body = (
        "<p>Xin chao <strong>{name}</strong>,</p>"
        "<p>Ban vua duoc dang ky gui xe tai he thong Parking Manager.</p>"
        "<p>Vui long nhan vao link ben duoi de xac thuc email:</p>"
        "<p><a href=\"{url}\">{url}</a></p>"
        "<p>Thong tin dang ky:</p>"
        "<ul>"
        "<li>Bien so xe: {plate}</li>"
        "<li>Bai do xe: {lot}</li>"
        "</ul>"
        "<p>Cam on!</p>"
    ).format(
        name=parking_user.full_name,
        url=verify_url,
        plate=parking_user.license_plate,
        lot=parking_user.parking_lot.name,
    )

    try:
        send_mail(
            subject,
            text_body,
            settings.DEFAULT_FROM_EMAIL,
            [email_value],
            fail_silently=False,
            html_message=html_body,
        )
    except Exception as exc:
        return False, str(exc)

    return True, None
