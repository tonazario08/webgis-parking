# WebGIS Parking Management System

## 1. Giới thiệu
**WebGIS Parking** là hệ thống quản lý và tìm kiếm bãi đỗ xe dựa trên nền tảng WebGIS.  
Hệ thống hỗ trợ hiển thị bản đồ, tìm bãi đỗ xe gần nhất, quản lý thông tin bãi đỗ, thống kê và phân tích dữ liệu phục vụ quản lý giao thông đô thị.

Dự án được xây dựng phục vụ học tập và nghiên cứu, hướng tới mô hình ứng dụng WebGIS trong quản lý hạ tầng giao thông.

---

## 2. Mục tiêu
- Hiển thị bản đồ các bãi đỗ xe trên nền WebGIS  
- Quản lý thông tin bãi đỗ xe (vị trí, sức chứa, trạng thái)  
- Hỗ trợ người dùng tìm bãi đỗ xe phù hợp  
- Thống kê, phân tích dữ liệu phục vụ quản lý  
- Xây dựng kiến trúc hệ thống WebGIS hoàn chỉnh

---

## 3. Công nghệ sử dụng
- **Backend**: Django  
- **Frontend GIS**: Leaflet / OpenLayers  
- **Cơ sở dữ liệu**: SQLite (giai đoạn phát triển), PostgreSQL + PostGIS (định hướng)  
- **Ngôn ngữ**: Python  
- **Quản lý mã nguồn**: Git, GitHub  

---

## 4. Cấu trúc thư mục

---

## 5. Cài đặt và chạy dự án

### 5.1 Clone repository
```bash
git clone https://github.com/tonazario08/webgis-parking.git
cd webgis-parking
5.2 Tạo môi trường ảo
python -m venv .venv
.venv\Scripts\activate
5.3 Cài đặt thư viện
pip install django
5.4 Chạy migrate
python manage.py migrate
5.5 Tạo tài khoản admin
python manage.py createsuperuser
5.6 Chạy server
python manage.py runserver
Truy cập:

Trang quản trị: http://127.0.0.1:8000/admin

Trang web: http://127.0.0.1:8000/

6. Quy ước làm việc nhóm
Nhánh main: phát hành chính thức

Nhánh dev: phát triển

Mỗi thành viên làm việc trên branch riêng

Merge vào dev thông qua Pull Request

7. Định hướng phát triển
Tích hợp PostGIS

Hiển thị tuyến đường tối ưu

Phân tích hotspot bãi đỗ xe

Dashboard thống kê trực quan

Nâng cấp giao diện WebGIS

8. Nhóm thực hiện
Sinh viên ngành Công nghệ Thông tin

Trường Đại học Tài nguyên và Môi trường

9. Ghi chú
Dự án phục vụ mục đích học tập và nghiên cứu, không sử dụng cho môi trường production.


👉 **Bước tiếp theo nên làm ngay**:  
- `git add README.md`  
- `git commit -m "Add README for WebGIS Parking project"`  
- `git push`

Nếu cần:  
- Chuẩn hóa lại README theo **đồ án tốt nghiệp**  
- Viết **mục phân công nhiệm vụ**  
- Vẽ **sơ đồ luồng WebGIS Parking**
