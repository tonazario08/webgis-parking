from django.shortcuts import render

def home(request):
    # Dữ liệu giả lập để hiển thị giao diện (Mock Data)
    context = {
        'total_parking': 12,
        'total_available': 450,
        'revenue': '24.5M',
        'active_areas': 3,
        # Danh sách bãi xe giả (ĐÃ THÊM ID VÀO ĐÂY)
        'parking_list': [
            {
                'id': 1,  # <--- Quan trọng: ID để link hoạt động
                'name': 'Vincom Đồng Khởi', 
                'address': 'Quận 1, TP.HCM', 
                'status': 'open', 
                'slots': 70, 
                'capacity': 100, 
                'percent': 70
            },
            {
                'id': 2,  # <--- Quan trọng: ID để link hoạt động
                'name': 'Bãi xe Bến Thành', 
                'address': 'Quận 1, TP.HCM', 
                'status': 'full', 
                'slots': 50, 
                'capacity': 50, 
                'percent': 100
            },
        ],
        # Lịch sử giả
        'activities': [
            {'action': 'Xe ra khỏi Vincom', 'time': 'Vừa xong', 'user': 'Admin'},
            {'action': 'Thêm bãi xe mới', 'time': '2 giờ trước', 'user': 'Quản lý'},
        ]
    }
    return render(request, 'parking/home.html', context)

def map_view(request):
    return render(request, 'parking/map.html')

def parking_list(request):
    return render(request, 'parking/parking_list.html')

def parking_available(request):
    return render(request, 'parking/parking_available.html')

def revenue_view(request):
    return render(request, 'parking/revenue.html')

def areas_view(request):
    return render(request, 'parking/areas.html')

# Hàm chi tiết bãi xe
def parking_detail(request, id):
    # Mock data chi tiết cho 1 bãi xe dựa trên ID
    context = {
        'parking': {
            'id': id,
            # Logic giả: Nếu id=1 thì hiện Vincom, còn lại hiện Bến Thành
            'name': 'Vincom Đồng Khởi' if id == 1 else 'Bãi xe Bến Thành',
            'address': '72 Lê Thánh Tôn, Quận 1, TP.HCM',
            'status': 'open' if id == 1 else 'full',
            'slots': 70 if id == 1 else 0,
            'capacity': 100 if id == 1 else 50,
            'price_per_hour': 20000,
        }
    }
    return render(request, 'parking/parking_detail.html', context)

def activity_log_view(request):
    # Mock data cho trang lịch sử
    context = {
        'logs': [
            {'time': '10:30 01/02/2026', 'user': 'Admin', 'action': 'Xe 51A-123.45 ra khỏi Vincom'},
            {'time': '10:15 01/02/2026', 'user': 'Bảo vệ', 'action': 'Xe 30E-999.99 vào Vincom'},
            {'time': '09:00 01/02/2026', 'user': 'Quản lý', 'action': 'Cập nhật giá vé ngày Tết'},
            {'time': '08:45 01/02/2026', 'user': 'System', 'action': 'Sao lưu dữ liệu tự động'},
            {'time': '18:30 31/01/2026', 'user': 'Bảo vệ', 'action': 'Xe 59C-567.89 vào Bến Thành'},
        ]
    }
    return render(request, 'parking/activity_log.html', context)
def activity_log_view(request):
    # 1. Lấy loại bộ lọc từ thanh địa chỉ (mặc định là 'all')
    filter_type = request.GET.get('filter', 'all')

    # 2. Dữ liệu gốc đầy đủ (Tôi đã thêm trường 'type' để phân loại)
    all_logs = [
        {'time': '10:30 01/02/2026', 'user': 'Admin', 'action': 'Xe 51A-123.45 ra khỏi Vincom', 'type': 'vehicle'},
        {'time': '10:15 01/02/2026', 'user': 'Bảo vệ', 'action': 'Xe 30E-999.99 vào Vincom', 'type': 'vehicle'},
        {'time': '09:00 01/02/2026', 'user': 'Quản lý', 'action': 'Cập nhật giá vé ngày Tết', 'type': 'system'},
        {'time': '08:45 01/02/2026', 'user': 'System', 'action': 'Sao lưu dữ liệu tự động', 'type': 'system'},
        {'time': '18:30 31/01/2026', 'user': 'Bảo vệ', 'action': 'Xe 59C-567.89 vào Bến Thành', 'type': 'vehicle'},
        {'time': '18:00 31/01/2026', 'user': 'System', 'action': 'Cảnh báo: Bãi xe Vincom sắp đầy (95%)', 'type': 'alert'},
    ]

    # 3. Logic lọc dữ liệu
    if filter_type == 'all':
        logs = all_logs
    else:
        # Giữ lại những dòng có 'type' trùng với bộ lọc
        logs = [log for log in all_logs if log['type'] == filter_type]

    # 4. Gửi dữ liệu và trạng thái lọc hiện tại ra ngoài template
    context = {
        'logs': logs,
        'current_filter': filter_type 
    }
    return render(request, 'parking/activity_log.html', context)