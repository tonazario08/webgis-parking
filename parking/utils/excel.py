from io import BytesIO
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from parking.models import Area, ParkingLot, ParkingPrice, ParkingRegistrationRequest, ParkingUser

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill(fill_type="solid", fgColor="2563EB")

_STATUS_LABELS = {
    "pending": "Chờ duyệt",
    "approved": "Đã duyệt",
    "rejected": "Không duyệt",
}

_VEHICLE_LABELS = {
    "car": "Ô tô",
    "motorbike": "Xe máy",
    "bike": "Xe đạp",
}


def _make_wb_with_header(headers: list) -> tuple:
    """Return (wb, ws) with styled header row."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
    return wb, ws


def _wb_to_bytes(wb) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_parkinglots_xlsx() -> bytes:
    headers = ["Tên bãi", "Địa chỉ", "Khu vực", "Quận/Huyện", "Sức chứa",
               "Vĩ độ", "Kinh độ", "Mô tả ngắn", "Trạng thái"]
    wb, ws = _make_wb_with_header(headers)
    for row, lot in enumerate(ParkingLot.objects.filter(is_deleted=False).select_related("area"), start=2):
        ws.cell(row=row, column=1, value=lot.name)
        ws.cell(row=row, column=2, value=lot.address)
        ws.cell(row=row, column=3, value=lot.area.name if lot.area else "")
        ws.cell(row=row, column=4, value=lot.district or "")
        ws.cell(row=row, column=5, value=lot.capacity)
        ws.cell(row=row, column=6, value=lot.latitude)
        ws.cell(row=row, column=7, value=lot.longitude)
        ws.cell(row=row, column=8, value=lot.short_description or "")
        ws.cell(row=row, column=9, value=1 if lot.is_active else 0)
    return _wb_to_bytes(wb)


def export_parkingusers_xlsx() -> bytes:
    headers = ["Họ tên", "Số điện thoại", "Email", "Địa chỉ",
               "Biển số xe", "Loại xe", "Bãi đỗ"]
    wb, ws = _make_wb_with_header(headers)
    for row, u in enumerate(ParkingUser.objects.filter(is_deleted=False).select_related("parking_lot"), start=2):
        ws.cell(row=row, column=1, value=u.full_name)
        ws.cell(row=row, column=2, value=u.phone)
        ws.cell(row=row, column=3, value=u.email or "")
        ws.cell(row=row, column=4, value=u.address or "")
        ws.cell(row=row, column=5, value=u.license_plate)
        ws.cell(row=row, column=6, value=_VEHICLE_LABELS.get(u.vehicle_type, u.vehicle_type))
        ws.cell(row=row, column=7, value=u.parking_lot.name if u.parking_lot else "")
    return _wb_to_bytes(wb)


def export_revenue_xlsx() -> bytes:
    headers = ["Tên bãi", "Khu vực", "Số xe hiện tại",
               "Doanh thu ước tính (VNĐ/giờ)", "Ngày xuất báo cáo"]
    wb, ws = _make_wb_with_header(headers)
    today = date.today().strftime("%d/%m/%Y")
    for row, lot in enumerate(ParkingLot.objects.filter(is_deleted=False).select_related("area"), start=2):
        active_count = ParkingUser.objects.filter(parking_lot=lot, is_active=True, is_deleted=False).count()
        revenue = sum(
            p.price_per_hour
            for p in ParkingPrice.objects.filter(parking_lot=lot)
        )
        ws.cell(row=row, column=1, value=lot.name)
        ws.cell(row=row, column=2, value=lot.area.name if lot.area else "")
        ws.cell(row=row, column=3, value=active_count)
        ws.cell(row=row, column=4, value=revenue)
        ws.cell(row=row, column=5, value=today)
    return _wb_to_bytes(wb)


def export_registrations_xlsx() -> bytes:
    headers = ["Họ tên", "Số điện thoại", "Email", "Biển số xe",
               "Loại xe", "Bãi đỗ đăng ký", "Trạng thái", "Ngày nộp đơn"]
    wb, ws = _make_wb_with_header(headers)
    qs = ParkingRegistrationRequest.objects.select_related("parking_lot").order_by("-created_at")
    for row, r in enumerate(qs, start=2):
        ws.cell(row=row, column=1, value=r.full_name)
        ws.cell(row=row, column=2, value=r.phone)
        ws.cell(row=row, column=3, value=r.email or "")
        ws.cell(row=row, column=4, value=r.license_plate)
        ws.cell(row=row, column=5, value=_VEHICLE_LABELS.get(r.vehicle_type, r.vehicle_type))
        ws.cell(row=row, column=6, value=r.parking_lot.name if r.parking_lot else "")
        ws.cell(row=row, column=7, value=_STATUS_LABELS.get(r.status, r.status))
        ws.cell(row=row, column=8, value=r.created_at.strftime("%d/%m/%Y %H:%M"))
    return _wb_to_bytes(wb)
