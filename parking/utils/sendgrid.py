import html
import requests

from django.conf import settings
from django.utils import timezone

SENDGRID_API_BASE = "https://api.sendgrid.com"
VALIDATION_PATH = "/v3/validations/email"
MAIL_SEND_PATH = "/v3/mail/send"


def _sendgrid_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def validate_email_address(email):
    require_validation = getattr(settings, "SENDGRID_REQUIRE_VALIDATION", True)
    api_key = getattr(settings, "SENDGRID_VALIDATION_API_KEY", "")

    if not api_key:
        if require_validation:
            return False, "Chua cau hinh SENDGRID_VALIDATION_API_KEY de xac thuc email.", None
        return True, None, None

    payload = {
        "email": email,
        "source": "parking_user",
    }
    try:
        res = requests.post(
            f"{SENDGRID_API_BASE}{VALIDATION_PATH}",
            json=payload,
            headers=_sendgrid_headers(api_key),
            timeout=10,
        )
    except requests.RequestException:
        return False, "Khong the ket noi SendGrid de xac thuc email.", None

    if res.status_code != 200:
        return False, "Khong the xac thuc email (SendGrid).", None

    data = res.json() or {}
    result = data.get("result") or {}
    verdict = result.get("verdict")
    suggestion = result.get("suggestion")

    if verdict != "Valid":
        msg = "Email khong hop le hoac co rui ro khong ton tai."
        if suggestion:
            msg += f" Goi y: {suggestion}."
        return False, msg, verdict

    return True, None, verdict


def build_parking_user_email(parking_user):
    created_at = parking_user.created_at
    if created_at is not None:
        created_at = timezone.localtime(created_at)
        created_text = created_at.strftime("%d/%m/%Y %H:%M")
    else:
        created_text = ""

    subject = "Thong tin gui xe - Parking GIS"
    full_name = html.escape(parking_user.full_name or "")
    phone = html.escape(parking_user.phone or "")
    email = html.escape(parking_user.email or "")
    address = html.escape(parking_user.address or "")
    license_plate = html.escape(parking_user.license_plate or "")
    vehicle_type = html.escape(parking_user.get_vehicle_type_display() if hasattr(parking_user, "get_vehicle_type_display") else (parking_user.vehicle_type or ""))
    parking_name = html.escape(str(parking_user.parking_lot) if parking_user.parking_lot_id else "")

    plain = "".join([
        "Cam on ban da dang ky gui xe.\n",
        "\n",
        f"Ho va ten: {full_name}\n",
        f"So dien thoai: {phone}\n",
        f"Email: {email}\n",
        f"Dia chi: {address}\n",
        f"Bien so xe: {license_plate}\n",
        f"Loai xe: {vehicle_type}\n",
        f"Bai do: {parking_name}\n",
        f"Thoi gian tao: {created_text}\n",
        "\n",
        "Vui long giu lai email nay de tra cuu thong tin khi can thiet.\n",
    ])

    html_body = f"""
    <div style=\"font-family: Arial, sans-serif; font-size: 14px; color: #1f2937;\">
      <h2 style=\"margin: 0 0 12px;\">Thong tin gui xe</h2>
      <p>Cam on ban da dang ky gui xe. Duoi day la thong tin chi tiet:</p>
      <table style=\"border-collapse: collapse; width: 100%; margin-top: 12px;\">
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Ho va ten</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{full_name}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">So dien thoai</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{phone}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Email</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{email}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Dia chi</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{address}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Bien so xe</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{license_plate}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Loai xe</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{vehicle_type}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Bai do</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{parking_name}</td></tr>
        <tr><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">Thoi gian tao</td><td style=\"padding: 6px 8px; border: 1px solid #e5e7eb;\">{created_text}</td></tr>
      </table>
      <p style=\"margin-top: 12px;\">Vui long giu lai email nay de tra cuu thong tin khi can thiet.</p>
    </div>
    """

    return subject, plain, html_body


def send_parking_user_email(parking_user):
    api_key = getattr(settings, "SENDGRID_API_KEY", "")
    from_email = getattr(settings, "SENDGRID_FROM_EMAIL", "")
    from_name = getattr(settings, "SENDGRID_FROM_NAME", "Parking GIS")

    if not api_key:
        return False, "Chua cau hinh SENDGRID_API_KEY de gui email."
    if not from_email:
        return False, "Chua cau hinh SENDGRID_FROM_EMAIL."

    to_email = (parking_user.email or "").strip()
    if not to_email:
        return False, "Chua nhap email de gui thong tin."

    subject, plain, html_body = build_parking_user_email(parking_user)

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {
            "email": from_email,
            "name": from_name,
        },
        "content": [
            {"type": "text/plain", "value": plain},
            {"type": "text/html", "value": html_body},
        ],
    }

    try:
        res = requests.post(
            f"{SENDGRID_API_BASE}{MAIL_SEND_PATH}",
            json=payload,
            headers=_sendgrid_headers(api_key),
            timeout=10,
        )
    except requests.RequestException:
        return False, "Khong the ket noi SendGrid de gui email."

    if res.status_code not in (200, 202):
        return False, "Gui email that bai. Vui long kiem tra cau hinh SendGrid."

    return True, None
