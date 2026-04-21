# Excel Import/Export — Design Spec
**Date:** 2026-04-21
**Status:** Approved

## Overview

Thêm chức năng nhập liệu từ Excel (import) và xuất Excel (export) vào khu quản trị `/manager/`. Dùng thư viện `openpyxl` thuần, không framework thêm.

## Scope

| Dữ liệu | Import | Export |
|---|---|---|
| ParkingLot (bãi đỗ xe) | ✓ | ✓ |
| ParkingUser (xe đang gửi) | ✓ | ✓ |
| Revenue (doanh thu) | — | ✓ |
| ParkingRegistrationRequest (đơn đăng ký) | — | ✓ |

## Architecture

### Files thêm/sửa

```
parking/
├── utils/
│   └── excel.py              # (mới) toàn bộ logic đọc/ghi Excel
├── manager_views.py           # (sửa) thêm view import/export
├── manager_urls.py            # (sửa) thêm URL patterns
└── templates/parking/manager/
    └── excel.html             # (mới) trang tổng quan import/export
requirements.txt               # (sửa) thêm openpyxl>=3.1
```

### URL Patterns (dưới `/manager/`)

| Method | URL | Chức năng |
|---|---|---|
| GET | `/manager/excel/` | Trang tổng quan |
| GET | `/manager/excel/template/<entity>/` | Tải file mẫu |
| POST | `/manager/excel/import/<entity>/` | Upload + import |
| GET | `/manager/excel/export/<entity>/` | Xuất Excel |

`<entity>` nhận: `parkinglots`, `parkingusers`, `revenue`, `registrations`

### Dependency

```
openpyxl>=3.1
```

## Excel Schema

### ParkingLot (import & export)

| Cột header | Field DB | Bắt buộc | Ghi chú |
|---|---|---|---|
| Tên bãi | name | ✓ | |
| Địa chỉ | address | ✓ | |
| Khu vực | area | ✓ | Tra cứu `Area.name` |
| Quận/Huyện | district | | |
| Sức chứa | capacity | ✓ | Số nguyên dương |
| Vĩ độ | latitude | | |
| Kinh độ | longitude | | |
| Mô tả ngắn | short_description | | |
| Trạng thái | is_active | | `1` = hoạt động, `0` = tạm đóng |

### ParkingUser (import & export)

| Cột header | Field DB | Bắt buộc | Ghi chú |
|---|---|---|---|
| Họ tên | full_name | ✓ | |
| Số điện thoại | phone | ✓ | Unique |
| Email | email | | |
| Địa chỉ | address | | |
| Biển số xe | license_plate | ✓ | Unique |
| Loại xe | vehicle_type | ✓ | `car` / `motorbike` / `bike` |
| Bãi đỗ | parking_lot | ✓ | Tra cứu `ParkingLot.name` |

### Revenue (export only)

| Cột | Nguồn |
|---|---|
| Tên bãi | ParkingLot.name |
| Khu vực | Area.name |
| Số xe hiện tại | ParkingUser count (is_active=True) |
| Doanh thu ước tính (VNĐ/giờ) | sum(ParkingPrice.price_per_hour) per lot |
| Ngày xuất báo cáo | datetime.now() |

### ParkingRegistrationRequest (export only)

| Cột | Nguồn |
|---|---|
| Họ tên | full_name |
| Số điện thoại | phone |
| Email | email |
| Biển số xe | license_plate |
| Loại xe | vehicle_type |
| Bãi đỗ đăng ký | parking_lot.name |
| Trạng thái | status (hiển thị tiếng Việt) |
| Ngày nộp đơn | created_at |

## Import Logic

### Flow

```
Upload file → Parse tất cả dòng → Validate toàn bộ
     ↓ có lỗi bất kỳ                ↓ tất cả hợp lệ
Hiện danh sách lỗi             Lưu DB (atomic transaction)
(không lưu gì)                 Hiện thông báo thành công
```

### Validation rules

**ParkingLot:**
- Thiếu cột bắt buộc → lỗi cả file (không xử lý tiếp)
- `capacity` không phải số nguyên dương → báo dòng
- `area` không khớp `Area.name` trong DB → báo tên không tồn tại
- `is_active` không phải `0` hoặc `1` → mặc định `1`

**ParkingUser:**
- Thiếu cột bắt buộc → lỗi cả file
- `phone` trùng với DB → báo dòng và số điện thoại
- `license_plate` trùng với DB → báo dòng và biển số
- `vehicle_type` không thuộc `car/motorbike/bike` → báo dòng
- `parking_lot` không khớp `ParkingLot.name` trong DB → báo tên không tồn tại

**Atomicity:** Toàn bộ import trong `transaction.atomic()`. Lỗi bất kỳ → rollback tất cả, không lưu dữ liệu nào.

### Lỗi report format

Khi có lỗi, hiện bảng trên trang:
```
Dòng 3: Số điện thoại "0901234567" đã tồn tại trong hệ thống.
Dòng 5: Loại xe "truck" không hợp lệ. Chỉ chấp nhận: car, motorbike, bike.
Dòng 7: Bãi đỗ "Bãi ABC" không tìm thấy trong hệ thống.
```

## UI Design

### Trang `/manager/excel/`

Layout 2 cột (Import | Export), đặt trong manager base template:

```
┌─────────────────────────────────────────────────────┐
│  📊 Import / Export Excel                           │
├──────────────────────────┬──────────────────────────┤
│  IMPORT                  │  EXPORT                  │
│                          │                          │
│  Bãi đỗ xe               │  Bãi đỗ xe      [Xuất]  │
│  [Tải mẫu] [Upload]      │                          │
│                          │  Xe đang gửi    [Xuất]  │
│  Xe đang gửi             │                          │
│  [Tải mẫu] [Upload]      │  Doanh thu      [Xuất]  │
│                          │                          │
│                          │  Đơn đăng ký    [Xuất]  │
└──────────────────────────┴──────────────────────────┘
```

- **Tải mẫu** → download `.xlsx` có header + 1 dòng ví dụ
- **Upload** → form POST, kết quả hiện ngay trên trang (success banner hoặc bảng lỗi)
- **Xuất** → download file ngay lập tức, tên file có ngày giờ: `parkinglots_2026-04-21.xlsx`

### Phân quyền

Chỉ user có quyền manager (`is_manager_user()`) mới truy cập được. Tất cả view đều check `@manager_required`.

## File mẫu (template)

Mỗi file mẫu gồm:
- Row 1: Header tiếng Việt (bold, background xanh nhạt)
- Row 2: Dòng ví dụ với dữ liệu mẫu hợp lệ

## Out of scope

- Export theo filter/date range (có thể thêm sau)
- Import ảnh ParkingLotImage
- Bulk update (import hiện tại chỉ tạo mới, không update bản ghi đã có)
