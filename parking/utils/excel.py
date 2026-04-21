from io import BytesIO
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from django.db import transaction
from django.db.models import Prefetch

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
    lots = (
        ParkingLot.objects
        .filter(is_deleted=False)
        .select_related("area")
        .prefetch_related(
            Prefetch(
                "prices",
                queryset=ParkingPrice.objects.all(),
            ),
            Prefetch(
                "parkinguser_set",
                queryset=ParkingUser.objects.filter(is_active=True, is_deleted=False),
                to_attr="active_users",
            ),
        )
    )
    for row, lot in enumerate(lots, start=2):
        active_count = len(lot.active_users)
        revenue = sum(p.price_per_hour for p in lot.prices.all())
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


def get_parkinglots_template_xlsx() -> bytes:
    headers = ["Tên bãi", "Địa chỉ", "Khu vực", "Quận/Huyện",
               "Sức chứa", "Vĩ độ", "Kinh độ", "Mô tả ngắn", "Trạng thái"]
    wb, ws = _make_wb_with_header(headers)
    example = ["Bãi Trung Tâm", "123 Nguyễn Huệ, Q.1", "Khu Trung Tâm", "Quận 1",
               100, 10.7769, 106.7009, "Bãi xe trung tâm thành phố", 1]
    for col, val in enumerate(example, start=1):
        ws.cell(row=2, column=col, value=val)
    return _wb_to_bytes(wb)


def get_parkingusers_template_xlsx() -> bytes:
    headers = ["Họ tên", "Số điện thoại", "Email", "Địa chỉ",
               "Biển số xe", "Loại xe", "Bãi đỗ"]
    wb, ws = _make_wb_with_header(headers)
    example = ["Nguyễn Văn A", "0901234567", "a@email.com",
               "456 Lê Lợi, Q.1", "51A-12345", "car", "Bãi Trung Tâm"]
    for col, val in enumerate(example, start=1):
        ws.cell(row=2, column=col, value=val)
    return _wb_to_bytes(wb)


_PARKINGLOT_REQUIRED = {"Tên bãi", "Địa chỉ", "Khu vực", "Sức chứa"}
_PARKINGUSER_REQUIRED = {"Họ tên", "Số điện thoại", "Biển số xe", "Loại xe", "Bãi đỗ"}

_VEHICLE_TYPE_ALIASES = {
    "ô tô": "car",
    "xe máy": "motorbike",
    "xe đạp": "bike",
    "car": "car",
    "motorbike": "motorbike",
    "bike": "bike",
}


def _parse_sheet(ws) -> tuple:
    """Return (headers, rows_as_dicts). Row numbers are 1-based (matching Excel)."""
    headers = [cell.value for cell in ws[1]]
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None for v in row):
            continue
        rows.append({"_row": row_idx, **dict(zip(headers, row))})
    return headers, rows


def import_parkinglots_xlsx(file_bytes: bytes) -> list:
    """
    Parse and import ParkingLot rows from Excel bytes.
    Returns list of error strings. Empty list means success (data was saved).
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes))
    ws = wb.active
    headers, rows = _parse_sheet(ws)

    missing = _PARKINGLOT_REQUIRED - set(headers)
    if missing:
        return [f"File thiếu cột bắt buộc: {', '.join(missing)}"]

    area_map = {a.name: a for a in Area.objects.filter(is_deleted=False)}
    errors = []
    objects = []

    for r in rows:
        row_num = r["_row"]
        area_name = str(r.get("Khu vực") or "").strip()
        if area_name not in area_map:
            errors.append(f"Dòng {row_num}: Khu vực \"{area_name}\" không tìm thấy trong hệ thống.")
            continue

        try:
            capacity = int(r.get("Sức chứa") or 0)
            if capacity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"Dòng {row_num}: Sức chứa \"{r.get('Sức chứa')}\" không phải số nguyên dương.")
            continue

        is_active_raw = r.get("Trạng thái")
        try:
            is_active = bool(int(is_active_raw)) if is_active_raw is not None else True
        except (ValueError, TypeError):
            is_active = True

        name = str(r.get("Tên bãi") or "").strip()
        if not name:
            errors.append(f"Dòng {row_num}: Tên bãi không được để trống.")
            continue

        objects.append(ParkingLot(
            name=name,
            address=str(r.get("Địa chỉ") or "").strip(),
            area=area_map[area_name],
            district=str(r.get("Quận/Huyện") or "").strip(),
            capacity=capacity,
            latitude=r.get("Vĩ độ") or None,
            longitude=r.get("Kinh độ") or None,
            short_description=str(r.get("Mô tả ngắn") or "").strip(),
            is_active=is_active,
        ))

    if errors:
        return errors

    with transaction.atomic():
        ParkingLot.objects.bulk_create(objects)
    return []


def import_parkingusers_xlsx(file_bytes: bytes) -> list:
    """
    Parse and import ParkingUser rows from Excel bytes.
    Returns list of error strings. Empty list means success (data was saved).
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes))
    ws = wb.active
    headers, rows = _parse_sheet(ws)

    missing = _PARKINGUSER_REQUIRED - set(headers)
    if missing:
        return [f"File thiếu cột bắt buộc: {', '.join(missing)}"]

    lot_map = {l.name: l for l in ParkingLot.objects.filter(is_deleted=False)}
    existing_phones = set(ParkingUser.objects.values_list("phone", flat=True))
    existing_plates = set(ParkingUser.objects.values_list("license_plate", flat=True))

    errors = []
    objects = []

    for r in rows:
        row_num = r["_row"]
        phone = str(r.get("Số điện thoại") or "").strip()
        plate = str(r.get("Biển số xe") or "").strip()
        vehicle_type = _VEHICLE_TYPE_ALIASES.get(str(r.get("Loại xe") or "").strip().lower(), "")
        lot_name = str(r.get("Bãi đỗ") or "").strip()

        if phone in existing_phones:
            errors.append(f"Dòng {row_num}: Số điện thoại \"{phone}\" đã tồn tại trong hệ thống.")
            continue
        if plate in existing_plates:
            errors.append(f"Dòng {row_num}: Biển số xe \"{plate}\" đã tồn tại trong hệ thống.")
            continue
        if not vehicle_type:
            errors.append(f"Dòng {row_num}: Loại xe \"{r.get('Loại xe')}\" không hợp lệ. Chỉ chấp nhận: car (Ô tô), motorbike (Xe máy), bike (Xe đạp).")
            continue
        if lot_name not in lot_map:
            errors.append(f"Dòng {row_num}: Bãi đỗ \"{lot_name}\" không tìm thấy trong hệ thống.")
            continue

        full_name = str(r.get("Họ tên") or "").strip()
        if not full_name:
            errors.append(f"Dòng {row_num}: Họ tên không được để trống.")
            continue

        existing_phones.add(phone)
        existing_plates.add(plate)
        objects.append(ParkingUser(
            full_name=full_name,
            phone=phone,
            email=str(r.get("Email") or "").strip() or "",
            address=str(r.get("Địa chỉ") or "").strip() or "",
            license_plate=plate,
            vehicle_type=vehicle_type,
            parking_lot=lot_map[lot_name],
            is_active=True,
        ))

    if errors:
        return errors

    with transaction.atomic():
        ParkingUser.objects.bulk_create(objects)
    return []
