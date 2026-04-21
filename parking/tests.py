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

    def test_export_parkingusers_has_data_row(self):
        wb = self._load_wb(export_parkingusers_xlsx())
        ws = wb.active
        self.assertEqual(ws.max_row, 2)  # header + 1 user

    def test_export_revenue_returns_bytes(self):
        result = export_revenue_xlsx()
        self.assertIsInstance(result, bytes)

    def test_export_revenue_has_header_row(self):
        wb = self._load_wb(export_revenue_xlsx())
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertIn("Tên bãi", headers)
        self.assertIn("Doanh thu ước tính (VNĐ/giờ)", headers)

    def test_export_revenue_has_data_row(self):
        wb = self._load_wb(export_revenue_xlsx())
        ws = wb.active
        self.assertEqual(ws.max_row, 2)  # header + 1 lot

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
