# Excel Import/Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm chức năng import/export Excel cho ParkingLot, ParkingUser, Revenue và ParkingRegistrationRequest trong khu quản trị `/manager/`.

**Architecture:** Toàn bộ logic đọc/ghi Excel nằm trong `parking/utils/excel.py`. Manager views gọi các hàm này và trả về HTTP response (file download hoặc render trang). Trang UI tập trung tại `/manager/excel/`.

**Tech Stack:** Django 6, openpyxl>=3.1, PostgreSQL, Bootstrap 5 (đã có trong manager base template)

---

## File Map

| File | Thay đổi | Trách nhiệm |
|---|---|---|
| `requirements.txt` | Sửa | Thêm `openpyxl>=3.1` |
| `parking/utils/excel.py` | Tạo mới | Toàn bộ logic đọc/ghi Excel |
| `parking/manager_views.py` | Sửa | 4 view mới: page, template, import, export |
| `parking/manager_urls.py` | Sửa | 4 URL pattern mới (đặt trước wildcard routes) |
| `parking/templates/parking/manager/excel.html` | Tạo mới | UI trang import/export |
| `parking/tests.py` | Sửa | Unit tests cho excel.py |

---

## Task 1: Thêm dependency openpyxl

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Thêm openpyxl vào requirements.txt**

Sửa `requirements.txt` thành:
```
Django==6.0.2
requests>=2.31,<3
psycopg2-binary>=2.9
python-dotenv>=1.0
openpyxl>=3.1
```

- [ ] **Step 2: Cài đặt**

```bash
source venv/Scripts/activate   # Windows Git Bash
pip install openpyxl
```

Expected: `Successfully installed openpyxl-3.x.x`

- [ ] **Step 3: Verify import**

```bash
python -c "import openpyxl; print(openpyxl.__version__)"
```

Expected: in ra version, ví dụ `3.1.5`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add openpyxl dependency for Excel import/export"
```

---

## Task 2: Tạo excel.py — Export functions

**Files:**
- Create: `parking/utils/excel.py`
- Test: `parking/tests.py`

### Bối cảnh
`parking/utils/` đã có `gis.py` và `email.py`. File mới `excel.py` theo cùng pattern: module-level functions, không class.

- [ ] **Step 1: Viết failing tests cho export functions**

Thêm vào `parking/tests.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from parking.models import Area, ParkingLot, ParkingUser, ParkingPrice, ParkingRegistrationRequest
from parking.utils.excel import (
    export_parkinglots_xlsx,
    export_parkingusers_xlsx,
    export_revenue_xlsx,
    export_registrations_xlsx,
)
import openpyxl
from io import BytesIO


class ExcelExportTest(TestCase):
    def setUp(self):
        self.area = Area.objects.create(
            name="Khu A", description="", latitude=10.0, longitude=106.0
        )
        self.lot = ParkingLot.objects.create(
            name="Bãi Test", address="123 Test", area=self.area,
            capacity=50, is_active=True, is_deleted=False,
        )
        self.user_auth = User.objects.create_user("staff1", password="pass")
        self.parking_user = ParkingUser.objects.create(
            full_name="Nguyễn Văn A", phone="0901234567",
            license_plate="51A-12345", vehicle_type="car",
            parking_lot=self.lot, is_active=True, is_deleted=False,
        )
        self.registration = ParkingRegistrationRequest.objects.create(
            full_name="Trần Thị B", phone="0912345678", email="b@test.com",
            address="456 Test", license_plate="59B-99999",
            vehicle_type="motorbike", parking_lot=self.lot,
            status="pending", created_by=self.user_auth,
        )

    def _load_wb(self, content: bytes):
        return openpyxl.load_workbook(BytesIO(content))

    def test_export_parkinglots_returns_bytes(self):
        result = export_parkinglots_xlsx()
        self.assertIsInstance(result, bytes)

    def test_export_parkinglots_has_header_row(self):
        wb = self._load_wb(export_parkinglots_xlsx())
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertIn("Tên bãi", headers)
        self.assertIn("Sức chứa", headers)

    def test_export_parkinglots_has_data_row(self):
        wb = self._load_wb(export_parkinglots_xlsx())
        ws = wb.active
        self.assertEqual(ws.max_row, 2)  # header + 1 lot

    def test_export_parkingusers_returns_bytes(self):
        result = export_parkingusers_xlsx()
        self.assertIsInstance(result, bytes)

    def test_export_parkingusers_has_header_row(self):
        wb = self._load_wb(export_parkingusers_xlsx())
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertIn("Họ tên", headers)
        self.assertIn("Biển số xe", headers)

    def test_export_revenue_returns_bytes(self):
        result = export_revenue_xlsx()
        self.assertIsInstance(result, bytes)

    def test_export_revenue_has_header_row(self):
        wb = self._load_wb(export_revenue_xlsx())
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertIn("Tên bãi", headers)
        self.assertIn("Doanh thu ước tính (VNĐ/giờ)", headers)

    def test_export_registrations_returns_bytes(self):
        result = export_registrations_xlsx()
        self.assertIsInstance(result, bytes)

    def test_export_registrations_status_vietnamese(self):
        wb = self._load_wb(export_registrations_xlsx())
        ws = wb.active
        # Find status column index
        headers = [cell.value for cell in ws[1]]
        status_idx = headers.index("Trạng thái") + 1
        self.assertEqual(ws.cell(row=2, column=status_idx).value, "Chờ duyệt")
```

- [ ] **Step 2: Chạy tests để xác nhận fail**

```bash
python manage.py test parking.tests.ExcelExportTest -v 2
```

Expected: `ImportError: cannot import name 'export_parkinglots_xlsx' from 'parking.utils.excel'`

- [ ] **Step 3: Tạo parking/utils/excel.py với export functions**

```python
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


def _make_wb_with_header(headers: list[str]) -> tuple:
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
```

- [ ] **Step 4: Chạy tests để xác nhận pass**

```bash
python manage.py test parking.tests.ExcelExportTest -v 2
```

Expected: `OK` — tất cả tests pass.

- [ ] **Step 5: Commit**

```bash
git add parking/utils/excel.py parking/tests.py requirements.txt
git commit -m "feat: add Excel export functions for parkinglots, parkingusers, revenue, registrations"
```

---

## Task 3: Thêm template download và import functions vào excel.py

**Files:**
- Modify: `parking/utils/excel.py`
- Modify: `parking/tests.py`

- [ ] **Step 1: Viết failing tests cho template và import**

Thêm vào `parking/tests.py` (sau class `ExcelExportTest`):

```python
from parking.utils.excel import (
    get_parkinglots_template_xlsx,
    get_parkingusers_template_xlsx,
    import_parkinglots_xlsx,
    import_parkingusers_xlsx,
)


class ExcelTemplateTest(TestCase):
    def _load_wb(self, content: bytes):
        return openpyxl.load_workbook(BytesIO(content))

    def test_parkinglots_template_has_example_row(self):
        wb = self._load_wb(get_parkinglots_template_xlsx())
        ws = wb.active
        self.assertEqual(ws.max_row, 2)

    def test_parkingusers_template_has_example_row(self):
        wb = self._load_wb(get_parkingusers_template_xlsx())
        ws = wb.active
        self.assertEqual(ws.max_row, 2)


class ExcelImportTest(TestCase):
    def setUp(self):
        self.area = Area.objects.create(
            name="Khu Test", description="", latitude=10.0, longitude=106.0
        )
        self.lot = ParkingLot.objects.create(
            name="Bãi Hiện Có", address="123", area=self.area,
            capacity=10, is_active=True, is_deleted=False,
        )
        self.existing_user = ParkingUser.objects.create(
            full_name="User Cũ", phone="0900000000",
            license_plate="51A-00000", vehicle_type="car",
            parking_lot=self.lot, is_active=True, is_deleted=False,
        )

    def _make_parkinglots_xlsx(self, rows: list[list]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Tên bãi", "Địa chỉ", "Khu vực", "Quận/Huyện",
                   "Sức chứa", "Vĩ độ", "Kinh độ", "Mô tả ngắn", "Trạng thái"])
        for row in rows:
            ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _make_parkingusers_xlsx(self, rows: list[list]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Họ tên", "Số điện thoại", "Email", "Địa chỉ",
                   "Biển số xe", "Loại xe", "Bãi đỗ"])
        for row in rows:
            ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # --- ParkingLot import ---
    def test_import_parkinglots_success(self):
        data = self._make_parkinglots_xlsx([
            ["Bãi Mới", "456 Đường B", "Khu Test", "Q.1", 30, 10.1, 106.1, "Mô tả", 1]
        ])
        errors = import_parkinglots_xlsx(data)
        self.assertEqual(errors, [])
        self.assertTrue(ParkingLot.objects.filter(name="Bãi Mới").exists())

    def test_import_parkinglots_invalid_area(self):
        data = self._make_parkinglots_xlsx([
            ["Bãi X", "789", "Khu Không Tồn Tại", "", 20, None, None, "", 1]
        ])
        errors = import_parkinglots_xlsx(data)
        self.assertGreater(len(errors), 0)
        self.assertFalse(ParkingLot.objects.filter(name="Bãi X").exists())

    def test_import_parkinglots_invalid_capacity(self):
        data = self._make_parkinglots_xlsx([
            ["Bãi Y", "789", "Khu Test", "", "abc", None, None, "", 1]
        ])
        errors = import_parkinglots_xlsx(data)
        self.assertGreater(len(errors), 0)
        self.assertFalse(ParkingLot.objects.filter(name="Bãi Y").exists())

    # --- ParkingUser import ---
    def test_import_parkingusers_success(self):
        data = self._make_parkingusers_xlsx([
            ["Nguyễn Mới", "0988888888", "new@test.com", "Địa chỉ mới",
             "51C-99999", "car", "Bãi Hiện Có"]
        ])
        errors = import_parkingusers_xlsx(data)
        self.assertEqual(errors, [])
        self.assertTrue(ParkingUser.objects.filter(phone="0988888888").exists())

    def test_import_parkingusers_duplicate_phone(self):
        data = self._make_parkingusers_xlsx([
            ["Người Trùng", "0900000000", "", "", "51C-11111", "car", "Bãi Hiện Có"]
        ])
        errors = import_parkingusers_xlsx(data)
        self.assertGreater(len(errors), 0)
        self.assertEqual(ParkingUser.objects.filter(phone="0900000000").count(), 1)

    def test_import_parkingusers_duplicate_plate(self):
        data = self._make_parkingusers_xlsx([
            ["Người Trùng", "0977777777", "", "", "51A-00000", "car", "Bãi Hiện Có"]
        ])
        errors = import_parkingusers_xlsx(data)
        self.assertGreater(len(errors), 0)

    def test_import_parkingusers_invalid_vehicle_type(self):
        data = self._make_parkingusers_xlsx([
            ["Người Mới", "0966666666", "", "", "51D-22222", "truck", "Bãi Hiện Có"]
        ])
        errors = import_parkingusers_xlsx(data)
        self.assertGreater(len(errors), 0)

    def test_import_parkingusers_invalid_lot(self):
        data = self._make_parkingusers_xlsx([
            ["Người Mới", "0955555555", "", "", "51E-33333", "car", "Bãi Không Tồn Tại"]
        ])
        errors = import_parkingusers_xlsx(data)
        self.assertGreater(len(errors), 0)
```

- [ ] **Step 2: Chạy tests để xác nhận fail**

```bash
python manage.py test parking.tests.ExcelTemplateTest parking.tests.ExcelImportTest -v 2
```

Expected: `ImportError: cannot import name 'get_parkinglots_template_xlsx'`

- [ ] **Step 3: Thêm template và import functions vào parking/utils/excel.py**

Thêm vào cuối file `parking/utils/excel.py`:

```python
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
_VALID_VEHICLE_TYPES = {"car", "motorbike", "bike"}


def _parse_sheet(ws) -> tuple[list[str], list[dict]]:
    """Return (headers, rows_as_dicts). Row numbers are 1-based (matching Excel)."""
    headers = [cell.value for cell in ws[1]]
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None for v in row):
            continue
        rows.append({"_row": row_idx, **dict(zip(headers, row))})
    return headers, rows


def import_parkinglots_xlsx(file_bytes: bytes) -> list[str]:
    """
    Parse and import ParkingLot rows from Excel bytes.
    Returns list of error strings. Empty list means success (data was saved).
    """
    from django.db import transaction

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

        objects.append(ParkingLot(
            name=str(r.get("Tên bãi") or "").strip(),
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


def import_parkingusers_xlsx(file_bytes: bytes) -> list[str]:
    """
    Parse and import ParkingUser rows from Excel bytes.
    Returns list of error strings. Empty list means success (data was saved).
    """
    from django.db import transaction

    wb = openpyxl.load_workbook(BytesIO(file_bytes))
    ws = wb.active
    headers, rows = _parse_sheet(ws)

    missing = _PARKINGUSER_REQUIRED - set(headers)
    if missing:
        return [f"File thiếu cột bắt buộc: {', '.join(missing)}"]

    lot_map = {l.name: l for l in ParkingLot.objects.filter(is_deleted=False)}
    existing_phones = set(ParkingUser.objects.filter(is_deleted=False).values_list("phone", flat=True))
    existing_plates = set(ParkingUser.objects.filter(is_deleted=False).values_list("license_plate", flat=True))

    errors = []
    objects = []

    for r in rows:
        row_num = r["_row"]
        phone = str(r.get("Số điện thoại") or "").strip()
        plate = str(r.get("Biển số xe") or "").strip()
        vehicle_type = str(r.get("Loại xe") or "").strip().lower()
        lot_name = str(r.get("Bãi đỗ") or "").strip()

        if phone in existing_phones:
            errors.append(f"Dòng {row_num}: Số điện thoại \"{phone}\" đã tồn tại trong hệ thống.")
            continue
        if plate in existing_plates:
            errors.append(f"Dòng {row_num}: Biển số xe \"{plate}\" đã tồn tại trong hệ thống.")
            continue
        if vehicle_type not in _VALID_VEHICLE_TYPES:
            errors.append(f"Dòng {row_num}: Loại xe \"{vehicle_type}\" không hợp lệ. Chỉ chấp nhận: car, motorbike, bike.")
            continue
        if lot_name not in lot_map:
            errors.append(f"Dòng {row_num}: Bãi đỗ \"{lot_name}\" không tìm thấy trong hệ thống.")
            continue

        existing_phones.add(phone)
        existing_plates.add(plate)
        objects.append(ParkingUser(
            full_name=str(r.get("Họ tên") or "").strip(),
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
```

- [ ] **Step 4: Chạy tất cả excel tests**

```bash
python manage.py test parking.tests.ExcelExportTest parking.tests.ExcelTemplateTest parking.tests.ExcelImportTest -v 2
```

Expected: `OK` — tất cả pass.

- [ ] **Step 5: Commit**

```bash
git add parking/utils/excel.py parking/tests.py
git commit -m "feat: add Excel template download and import functions"
```

---

## Task 4: Thêm Views và URLs

**Files:**
- Modify: `parking/manager_views.py`
- Modify: `parking/manager_urls.py`

- [ ] **Step 1: Thêm imports vào đầu manager_views.py**

Tìm block import ở đầu file `parking/manager_views.py` và thêm:

```python
from django.http import HttpResponse
```

(Nếu đã có `HttpResponse` trong imports thì bỏ qua bước này.)

- [ ] **Step 2: Thêm 4 view vào cuối manager_views.py**

Thêm vào **cuối** file `parking/manager_views.py`:

```python
@login_required(login_url="manager_login")
def manager_excel_page(request):
    return render(request, "parking/manager/excel.html")


@login_required(login_url="manager_login")
def manager_excel_template(request, entity):
    from parking.utils.excel import get_parkinglots_template_xlsx, get_parkingusers_template_xlsx

    templates = {
        "parkinglots": ("parkinglots_mau.xlsx", get_parkinglots_template_xlsx),
        "parkingusers": ("parkingusers_mau.xlsx", get_parkingusers_template_xlsx),
    }
    if entity not in templates:
        from django.http import Http404
        raise Http404

    filename, fn = templates[entity]
    response = HttpResponse(
        fn(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="manager_login")
def manager_excel_import(request, entity):
    from parking.utils.excel import import_parkinglots_xlsx, import_parkingusers_xlsx

    if request.method != "POST":
        return redirect("manager_excel")

    importers = {
        "parkinglots": import_parkinglots_xlsx,
        "parkingusers": import_parkingusers_xlsx,
    }
    if entity not in importers:
        from django.http import Http404
        raise Http404

    upload = request.FILES.get("file")
    if not upload:
        messages.error(request, "Vui lòng chọn file Excel để import.")
        return redirect("manager_excel")

    errors = importers[entity](upload.read())
    if errors:
        return render(request, "parking/manager/excel.html", {
            "import_errors": errors,
            "import_entity": entity,
        })

    label = "Bãi đỗ xe" if entity == "parkinglots" else "Xe đang gửi"
    messages.success(request, f"Import {label} thành công.")
    return redirect("manager_excel")


@login_required(login_url="manager_login")
def manager_excel_export(request, entity):
    from parking.utils.excel import (
        export_parkinglots_xlsx,
        export_parkingusers_xlsx,
        export_revenue_xlsx,
        export_registrations_xlsx,
    )
    from datetime import date

    exporters = {
        "parkinglots": ("parkinglots", export_parkinglots_xlsx),
        "parkingusers": ("parkingusers", export_parkingusers_xlsx),
        "revenue": ("doanh_thu", export_revenue_xlsx),
        "registrations": ("don_dang_ky", export_registrations_xlsx),
    }
    if entity not in exporters:
        from django.http import Http404
        raise Http404

    slug, fn = exporters[entity]
    filename = f"{slug}_{date.today().strftime('%Y-%m-%d')}.xlsx"
    response = HttpResponse(
        fn(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
```

- [ ] **Step 3: Thêm URL patterns vào manager_urls.py**

Mở `parking/manager_urls.py`. Thêm 4 dòng sau vào **trước** dòng `path("roles/", ...)` (tức là trước các wildcard `<str:entity>/`):

```python
path("excel/", manager_views.manager_excel_page, name="manager_excel"),
path("excel/template/<str:entity>/", manager_views.manager_excel_template, name="manager_excel_template"),
path("excel/import/<str:entity>/", manager_views.manager_excel_import, name="manager_excel_import"),
path("excel/export/<str:entity>/", manager_views.manager_excel_export, name="manager_excel_export"),
```

- [ ] **Step 4: Kiểm tra syntax**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add parking/manager_views.py parking/manager_urls.py
git commit -m "feat: add Excel import/export views and URLs"
```

---

## Task 5: Tạo template excel.html

**Files:**
- Create: `parking/templates/parking/manager/excel.html`

- [ ] **Step 1: Tạo file template**

Tạo file `parking/templates/parking/manager/excel.html`:

```html
{% extends "parking/manager/base.html" %}

{% block title %}Import / Export Excel{% endblock %}

{% block content %}
<div class="container-fluid px-4 py-4">
    <div class="d-flex align-items-center gap-3 mb-4">
        <h1 class="h3 mb-0 fw-bold">Import / Export Excel</h1>
    </div>

    {% if messages %}
    {% for msg in messages %}
    <div class="alert alert-{{ msg.tags }} alert-dismissible fade show" role="alert">
        {{ msg }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
    {% endif %}

    {% if import_errors %}
    <div class="alert alert-danger mb-4">
        <h6 class="fw-bold mb-2"><i class="fas fa-exclamation-triangle me-2"></i>Import thất bại — không có dữ liệu nào được lưu</h6>
        <ul class="mb-0 ps-3">
            {% for err in import_errors %}
            <li>{{ err }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="row g-4">
        <!-- IMPORT -->
        <div class="col-lg-6">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-header bg-white border-bottom fw-bold py-3">
                    <i class="fas fa-file-import me-2 text-primary"></i>Import từ Excel
                </div>
                <div class="card-body">

                    <!-- ParkingLot import -->
                    <div class="mb-4">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-semibold">Bãi đỗ xe</span>
                            <a href="{% url 'manager_excel_template' 'parkinglots' %}"
                               class="btn btn-sm btn-outline-secondary">
                                <i class="fas fa-download me-1"></i>Tải mẫu
                            </a>
                        </div>
                        <form method="post" action="{% url 'manager_excel_import' 'parkinglots' %}"
                              enctype="multipart/form-data" class="d-flex gap-2">
                            {% csrf_token %}
                            <input type="file" name="file" accept=".xlsx" class="form-control form-control-sm" required>
                            <button type="submit" class="btn btn-sm btn-primary text-nowrap">
                                <i class="fas fa-upload me-1"></i>Import
                            </button>
                        </form>
                    </div>

                    <hr>

                    <!-- ParkingUser import -->
                    <div class="mb-2">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-semibold">Xe đang gửi</span>
                            <a href="{% url 'manager_excel_template' 'parkingusers' %}"
                               class="btn btn-sm btn-outline-secondary">
                                <i class="fas fa-download me-1"></i>Tải mẫu
                            </a>
                        </div>
                        <form method="post" action="{% url 'manager_excel_import' 'parkingusers' %}"
                              enctype="multipart/form-data" class="d-flex gap-2">
                            {% csrf_token %}
                            <input type="file" name="file" accept=".xlsx" class="form-control form-control-sm" required>
                            <button type="submit" class="btn btn-sm btn-primary text-nowrap">
                                <i class="fas fa-upload me-1"></i>Import
                            </button>
                        </form>
                    </div>

                </div>
            </div>
        </div>

        <!-- EXPORT -->
        <div class="col-lg-6">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-header bg-white border-bottom fw-bold py-3">
                    <i class="fas fa-file-export me-2 text-success"></i>Xuất ra Excel
                </div>
                <div class="card-body">

                    {% for entity, label, icon in export_items %}
                    <div class="d-flex align-items-center justify-content-between py-2 {% if not forloop.last %}border-bottom{% endif %}">
                        <span class="fw-semibold"><i class="{{ icon }} me-2 text-muted"></i>{{ label }}</span>
                        <a href="{% url 'manager_excel_export' entity %}"
                           class="btn btn-sm btn-outline-success">
                            <i class="fas fa-download me-1"></i>Xuất
                        </a>
                    </div>
                    {% endfor %}

                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Truyền export_items context từ view**

`export_items` cần được truyền từ view. Sửa `manager_excel_page` trong `parking/manager_views.py`:

```python
@login_required(login_url="manager_login")
def manager_excel_page(request):
    export_items = [
        ("parkinglots", "Bãi đỗ xe", "fas fa-parking"),
        ("parkingusers", "Xe đang gửi", "fas fa-car"),
        ("revenue", "Doanh thu", "fas fa-chart-line"),
        ("registrations", "Đơn đăng ký", "fas fa-file-alt"),
    ]
    return render(request, "parking/manager/excel.html", {"export_items": export_items})
```

- [ ] **Step 3: Thêm link "Excel" vào sidebar của manager base template**

Mở `parking/templates/parking/manager/base.html`. Tìm link sidebar "Doanh thu" và thêm sau nó:

```html
<li class="nav-item">
    <a class="nav-link {% if request.resolver_match.url_name == 'manager_excel' %}active{% endif %}"
       href="{% url 'manager_excel' %}">
        <i class="fas fa-file-excel me-2"></i>Import / Export
    </a>
</li>
```

- [ ] **Step 4: Kiểm tra**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add parking/templates/parking/manager/excel.html parking/templates/parking/manager/base.html parking/manager_views.py
git commit -m "feat: add Excel import/export UI page and sidebar link"
```

---

## Task 6: Kiểm tra end-to-end và push

- [ ] **Step 1: Chạy toàn bộ test suite**

```bash
python manage.py test parking -v 2
```

Expected: `OK` — không có failures.

- [ ] **Step 2: Khởi động server và kiểm tra thủ công**

```bash
python manage.py runserver
```

Truy cập `/manager/excel/` và kiểm tra:
- [ ] Trang load đúng, có 2 cột Import/Export
- [ ] Nút "Tải mẫu" download file `.xlsx` có header + dòng ví dụ
- [ ] Upload file mẫu → thành công, hiện flash message
- [ ] Upload file với lỗi (sửa loại xe thành "truck") → hiện bảng lỗi, không lưu
- [ ] Các nút Xuất download file đúng tên (`parkinglots_YYYY-MM-DD.xlsx`, ...)
- [ ] Link "Import / Export" hiện trong sidebar

- [ ] **Step 3: Push lên cả hai nhánh**

```bash
git push origin dev
git push origin dev:feat/admin-404-perm-revenue-vn
```
