"""
GIS Utilities cho Hệ thống Quản lý Bãi đỗ xe Đô thị
===================================================

Module này chứa toàn bộ logic xử lý không gian (GIS) độc lập với Django views.
Các hàm có thể được sử dụng trực tiếp hoặc gọi từ API endpoints.

Chức năng chính:
1. Tính khoảng cách Haversine (great-circle distance)
2. Tìm bãi đỗ xe trong bán kính
3. Tính route tối ưu (sử dụng OSRM API)
4. Các hàm hỗ trợ GIS khác

Author: GIS Backend Team
Date: 2026-02-04
"""

import math
import json
from typing import List, Dict, Tuple, Optional, Any
from decimal import Decimal
import requests
from django.db.models import QuerySet


# =============================================================================
# CONSTANTS - HỆ THỐNG TỌA ĐỘ
# =============================================================================

EARTH_RADIUS_KM = 6371.0  # Bán kính trái đất (km) - chuẩn WGS84
METERS_PER_KM = 1000.0
DEGREES_TO_RADIANS = math.pi / 180.0


# =============================================================================
# 1. HAVERSINE DISTANCE - TÍNH KHOẢNG CÁCH GREAT-CIRCLE
# =============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa 2 điểm trên mặt cầu sử dụng công thức Haversine.
    
    Công thức Haversine:
    --------------------
    a = sin²(Δφ/2) + cos(φ1) × cos(φ2) × sin²(Δλ/2)
    c = 2 × atan2(√a, √(1−a))
    d = R × c
    
    Trong đó:
    - φ (phi): latitude (vĩ độ)
    - λ (lambda): longitude (kinh độ)
    - R: bán kính trái đất (6371 km)
    - d: khoảng cách (km)
    
    Ưu điểm:
    --------
    - Chính xác cho khoảng cách ngắn-trung bình (< 1000km)
    - Không cần thư viện GIS nặng (PostGIS, Shapely)
    - Tốc độ nhanh, phù hợp real-time queries
    
    Độ chính xác:
    -------------
    - Sai số < 0.5% cho khoảng cách < 500km
    - Phù hợp cho ứng dụng đô thị (bán kính thường < 50km)
    
    Args:
        lat1 (float): Vĩ độ điểm 1 (degrees)
        lon1 (float): Kinh độ điểm 1 (degrees)
        lat2 (float): Vĩ độ điểm 2 (degrees)
        lon2 (float): Kinh độ điểm 2 (degrees)
    
    Returns:
        float: Khoảng cách (km), làm tròn 2 chữ số thập phân
    
    Example:
        >>> # Khoảng cách từ Quận 1 đến Thủ Đức, TP.HCM
        >>> distance = haversine_distance(10.762622, 106.660172, 10.850002, 106.771482)
        >>> print(f"{distance:.2f} km")  # Output: ~16.28 km
    
    References:
        - https://en.wikipedia.org/wiki/Haversine_formula
        - Sinnott, R. W. (1984). "Virtues of the Haversine"
    """
    # Chuyển đổi độ sang radian (degrees → radians)
    lat1_rad = lat1 * DEGREES_TO_RADIANS
    lon1_rad = lon1 * DEGREES_TO_RADIANS
    lat2_rad = lat2 * DEGREES_TO_RADIANS
    lon2_rad = lon2 * DEGREES_TO_RADIANS
    
    # Tính delta (hiệu số) giữa 2 điểm
    dlat = lat2_rad - lat1_rad  # Δφ
    dlon = lon2_rad - lon1_rad  # Δλ
    
    # Áp dụng công thức Haversine
    # Bước 1: Tính a = sin²(Δφ/2) + cos(φ1) × cos(φ2) × sin²(Δλ/2)
    a = (
        math.sin(dlat / 2.0) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    )
    
    # Bước 2: Tính c = 2 × atan2(√a, √(1−a))
    # atan2 xử lý tốt hơn atan trong trường hợp biên
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Bước 3: Tính khoảng cách d = R × c
    distance_km = EARTH_RADIUS_KM * c
    
    # Làm tròn 2 chữ số thập phân (độ chính xác ~10m)
    return round(distance_km, 2)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa 2 điểm, trả về đơn vị mét.
    
    Args:
        lat1, lon1, lat2, lon2: Tọa độ 2 điểm (degrees)
    
    Returns:
        float: Khoảng cách (mét)
    
    Example:
        >>> distance_m = haversine_distance_meters(10.762622, 106.660172, 10.763000, 106.661000)
        >>> print(f"{distance_m:.1f}m")  # Output: ~116.5m
    """
    distance_km = haversine_distance(lat1, lon1, lat2, lon2)
    return round(distance_km * METERS_PER_KM, 1)


# =============================================================================
# 2. BOUNDING BOX - TỐI ƯU HÓA QUERIES
# =============================================================================

def calculate_bounding_box(lat: float, lon: float, radius_km: float) -> Dict[str, float]:
    """
    Tính bounding box (hình chữ nhật bao quanh) từ điểm trung tâm và bán kính.
    
    Mục đích:
    ---------
    Thay vì tính khoảng cách Haversine cho TẤT CẢ bãi đỗ trong database,
    ta lọc sơ bộ bằng bounding box (WHERE lat BETWEEN ... AND lon BETWEEN ...)
    → Giảm số lượng tính toán từ N xuống ~N/100
    
    Công thức:
    ----------
    Δlat = radius / R  (R = Earth radius)
    Δlon = radius / (R × cos(lat))
    
    min_lat = lat - Δlat
    max_lat = lat + Δlat
    min_lon = lon - Δlon
    max_lon = lon + Δlon
    
    Lưu ý:
    ------
    - Công thức này là xấp xỉ, chính xác cho khoảng cách nhỏ
    - Ở gần cực (lat > 80°), cos(lat) → 0 → Δlon rất lớn
    - Trong ứng dụng đô thị (lat ~10-20°), sai số < 1%
    
    Args:
        lat (float): Vĩ độ điểm trung tâm
        lon (float): Kinh độ điểm trung tâm
        radius_km (float): Bán kính tìm kiếm (km)
    
    Returns:
        dict: {
            'min_lat': float,
            'max_lat': float,
            'min_lon': float,
            'max_lon': float
        }
    
    Example:
        >>> # Tìm bounding box bán kính 5km quanh Bến Thành
        >>> bbox = calculate_bounding_box(10.762622, 106.660172, 5.0)
        >>> print(bbox)
        {
            'min_lat': 10.7177,
            'max_lat': 10.8075,
            'min_lon': 106.6052,
            'max_lon': 106.7151
        }
    """
    # Chuyển latitude sang radian
    lat_rad = lat * DEGREES_TO_RADIANS
    
    # Tính delta latitude (độ)
    # 1 degree latitude ≈ 111.32 km (constant)
    delta_lat = radius_km / 111.32
    
    # Tính delta longitude (độ)
    # 1 degree longitude = 111.32 × cos(latitude) km (varies with latitude)
    delta_lon = radius_km / (111.32 * math.cos(lat_rad))
    
    # Tính các cạnh của bounding box
    min_lat = lat - delta_lat
    max_lat = lat + delta_lat
    min_lon = lon - delta_lon
    max_lon = lon + delta_lon
    
    return {
        'min_lat': round(min_lat, 6),
        'max_lat': round(max_lat, 6),
        'min_lon': round(min_lon, 6),
        'max_lon': round(max_lon, 6)
    }


# =============================================================================
# 3. TÌM BÃI ĐỖ XE TRONG BÁN KÍNH
# =============================================================================

def find_nearby_parkings(
    parking_queryset: QuerySet,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    only_active: bool = True,
    only_available: bool = False,
    min_slots: int = 0,
    sort_by_distance: bool = True
) -> List[Dict[str, Any]]:
    """
    Tìm các bãi đỗ xe trong bán kính từ điểm trung tâm.
    
    Thuật toán 2-bước (Two-phase algorithm):
    ----------------------------------------
    1. PHASE 1 - Rough Filter (Bounding Box):
       - Lọc nhanh bằng WHERE lat/lon BETWEEN
       - Giảm số lượng records cần xử lý
       - Độ phức tạp: O(log N) với index
    
    2. PHASE 2 - Precise Filter (Haversine):
       - Tính khoảng cách chính xác cho từng bãi
       - Chỉ giữ lại bãi trong bán kính
       - Độ phức tạp: O(M) với M << N
    
    Tối ưu hóa:
    -----------
    - Sử dụng select_related() để giảm queries
    - Index trên (latitude, longitude)
    - Early filtering (active, available)
    
    Args:
        parking_queryset (QuerySet): Django QuerySet của model Parking
        center_lat (float): Vĩ độ điểm trung tâm
        center_lon (float): Kinh độ điểm trung tâm
        radius_km (float): Bán kính tìm kiếm (km)
        only_active (bool): Chỉ lấy bãi đang hoạt động (default: True)
        only_available (bool): Chỉ lấy bãi còn chỗ (default: False)
        min_slots (int): Số chỗ trống tối thiểu (default: 0)
        sort_by_distance (bool): Sắp xếp theo khoảng cách (default: True)
    
    Returns:
        List[Dict]: Danh sách bãi đỗ xe, mỗi phần tử chứa:
            - id: ID bãi đỗ
            - name: Tên bãi
            - latitude, longitude: Tọa độ
            - distance_km: Khoảng cách từ điểm trung tâm
            - distance_meters: Khoảng cách (mét)
            - available_slots: Số chỗ trống
            - total_slots: Tổng số chỗ
            - capacity_percent: % chỗ trống
            - parking_type: Loại bãi
            - khu_vuc: Khu vực
            - address: Địa chỉ
            - status: Trạng thái bãi
            - ... (các field khác)
    
    Example:
        >>> from parking.models import Parking
        >>> parkings = find_nearby_parkings(
        ...     Parking.objects.all(),
        ...     center_lat=10.762622,
        ...     center_lon=106.660172,
        ...     radius_km=5.0,
        ...     only_available=True,
        ...     min_slots=10
        ... )
        >>> for p in parkings[:3]:
        ...     print(f"{p['name']}: {p['distance_km']}km, {p['available_slots']} chỗ")
    """
    # PHASE 1: Bounding Box Filter (Rough)
    # -------------------------------------
    bbox = calculate_bounding_box(center_lat, center_lon, radius_km)
    
    # Lọc trong bounding box + điều kiện bổ sung
    filtered_qs = parking_queryset.filter(
        latitude__gte=bbox['min_lat'],
        latitude__lte=bbox['max_lat'],
        longitude__gte=bbox['min_lon'],
        longitude__lte=bbox['max_lon']
    )
    
    # Chỉ lấy bãi đang hoạt động
    if only_active:
        filtered_qs = filtered_qs.filter(is_active=True)
    
    # Chỉ lấy bãi còn chỗ
    if only_available:
        filtered_qs = filtered_qs.filter(available_slots__gt=min_slots)
    
    # Tối ưu queries với select_related
    filtered_qs = filtered_qs.select_related('parking_type', 'khu_vuc')
    
    # PHASE 2: Haversine Distance Filter (Precise)
    # ---------------------------------------------
    results = []
    
    for parking in filtered_qs:
        # Chuyển Decimal sang float để tính toán
        p_lat = float(parking.latitude)
        p_lon = float(parking.longitude)
        
        # Tính khoảng cách chính xác
        distance_km = haversine_distance(center_lat, center_lon, p_lat, p_lon)
        
        # Chỉ giữ lại bãi trong bán kính
        if distance_km <= radius_km:
            # Tính các thông tin bổ sung
            capacity_percent = parking.get_capacity_percent()
            status = parking.get_status()
            
            # Build result object
            result = {
                'id': parking.id,
                'name': parking.name,
                'latitude': p_lat,
                'longitude': p_lon,
                'distance_km': distance_km,
                'distance_meters': round(distance_km * METERS_PER_KM, 1),
                'available_slots': parking.available_slots,
                'total_slots': parking.total_slots,
                'capacity_percent': capacity_percent,
                'is_full': parking.is_full(),
                'is_nearly_full': parking.is_nearly_full(),
                
                # Thông tin chi tiết
                'parking_type': {
                    'id': parking.parking_type.id,
                    'name': parking.parking_type.name,
                    'ownership': parking.parking_type.ownership,
                    'icon': parking.parking_type.map_icon
                },
                'khu_vuc': {
                    'id': parking.khu_vuc.id,
                    'name': parking.khu_vuc.name,
                    'code': parking.khu_vuc.code
                },
                'address': parking.address or '',
                'phone': parking.phone or '',
                
                # Giờ hoạt động
                'is_24h': parking.is_24h,
                'opening_time': parking.opening_time.strftime('%H:%M') if parking.opening_time else None,
                'closing_time': parking.closing_time.strftime('%H:%M') if parking.closing_time else None,
                
                # Tiện ích
                'has_security': parking.has_security,
                'has_camera': parking.has_camera,
                'has_ev_charging': parking.has_ev_charging,
                
                # Trạng thái
                'status': {
                    'name': status.name if status else 'Unknown',
                    'color': status.color_code if status else '#999999'
                } if status else None,
                
                # Metadata
                'created_at': parking.created_at.isoformat(),
            }
            
            results.append(result)
    
    # PHASE 3: Sorting (Optional)
    # ----------------------------
    if sort_by_distance:
        results.sort(key=lambda x: x['distance_km'])
    
    return results


# =============================================================================
# 4. ROUTE CALCULATION - TÍNH ĐƯỜNG ĐI TỐI ƯU
# =============================================================================

def calculate_route_osrm(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = 'driving'
) -> Optional[Dict[str, Any]]:
    """
    Tính route tối ưu sử dụng OSRM API (Open Source Routing Machine).
    
    OSRM Overview:
    --------------
    - Open-source routing engine
    - Dữ liệu từ OpenStreetMap
    - API miễn phí (có giới hạn rate)
    - Hỗ trợ: driving, cycling, walking
    
    API Endpoint:
    -------------
    https://router.project-osrm.org/route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}
    
    Profile Options:
    ----------------
    - 'driving': Lái xe (default)
    - 'cycling': Đạp xe
    - 'walking': Đi bộ
    - 'driving-traffic': Xem xét traffic (nếu có)
    
    Response Format:
    ----------------
    {
        "code": "Ok",
        "routes": [{
            "geometry": "encoded_polyline",  # Encoded polyline
            "distance": 1234.5,              # Meters
            "duration": 123.4                # Seconds
        }]
    }
    
    Args:
        start_lat (float): Vĩ độ điểm bắt đầu
        start_lon (float): Kinh độ điểm bắt đầu
        end_lat (float): Vĩ độ điểm kết thúc
        end_lon (float): Kinh độ điểm kết thúc
        profile (str): Phương thức di chuyển (default: 'driving')
    
    Returns:
        dict hoặc None:
            - route_geometry: List of [lon, lat] coordinates
            - distance_km: Khoảng cách (km)
            - duration_minutes: Thời gian (phút)
            - steps: Các bước đi (nếu có)
            - None nếu có lỗi
    
    Example:
        >>> # Tính route từ Bến Thành đến Thủ Đức
        >>> route = calculate_route_osrm(10.762622, 106.660172, 10.850002, 106.771482)
        >>> if route:
        ...     print(f"Khoảng cách: {route['distance_km']}km")
        ...     print(f"Thời gian: {route['duration_minutes']} phút")
    
    Notes:
        - Cần kết nối internet
        - Rate limit: ~10 requests/second (free tier)
        - Có thể self-host OSRM nếu cần production
    
    Alternatives:
        - OpenRouteService: https://openrouteservice.org/
        - GraphHopper: https://www.graphhopper.com/
        - Google Directions API (trả phí)
    """
    try:
        # Build OSRM API URL
        # Format: lon,lat (OSRM uses lon,lat order, NOT lat,lon!)
        url = (
            f"https://router.project-osrm.org/route/v1/{profile}/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        
        # Gọi API với timeout 10s
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Kiểm tra response code
        if data.get('code') != 'Ok':
            return None
        
        # Parse route data
        routes = data.get('routes', [])
        if not routes:
            return None
        
        route = routes[0]  # Lấy route đầu tiên (tốt nhất)
        
        # Extract geometry (polyline coordinates)
        geometry = route.get('geometry', {})
        coordinates = geometry.get('coordinates', [])
        
        # Convert coordinates to more readable format
        # OSRM returns [lon, lat], ta convert sang [lat, lon] cho consistency
        route_points = [[lat, lon] for lon, lat in coordinates]
        
        # Extract distance & duration
        distance_meters = route.get('distance', 0)
        duration_seconds = route.get('duration', 0)
        
        # Extract steps (turn-by-turn directions)
        legs = route.get('legs', [])
        steps = []
        if legs:
            for step in legs[0].get('steps', []):
                steps.append({
                    'instruction': step.get('maneuver', {}).get('instruction', ''),
                    'distance_meters': step.get('distance', 0),
                    'duration_seconds': step.get('duration', 0),
                    'name': step.get('name', '')
                })
        
        return {
            'route_geometry': route_points,  # List of [lat, lon]
            'route_geometry_lonlat': coordinates,  # List of [lon, lat] for mapping
            'distance_km': round(distance_meters / 1000.0, 2),
            'distance_meters': round(distance_meters, 1),
            'duration_minutes': round(duration_seconds / 60.0, 1),
            'duration_seconds': round(duration_seconds, 1),
            'steps': steps,
            'profile': profile
        }
        
    except requests.exceptions.RequestException as e:
        # Network error, timeout, etc.
        print(f"OSRM API Error: {e}")
        return None
    except Exception as e:
        # JSON parse error, unexpected response, etc.
        print(f"Route calculation error: {e}")
        return None


def calculate_route_simple(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float
) -> Dict[str, Any]:
    """
    Tính route đơn giản (mô phỏng) khi không có API routing.
    
    Cảnh báo:
    ---------
    Đây là SIMULATION - KHÔNG phải route thực tế!
    Chỉ dùng cho mục đích demo/testing khi không có internet hoặc API.
    
    Logic:
    ------
    1. Vẽ đường thẳng từ điểm A đến B
    2. Chia thành N điểm trung gian
    3. Tính khoảng cách Haversine (as-the-crow-flies)
    4. Ước lượng thời gian (giả định tốc độ trung bình)
    
    Args:
        start_lat, start_lon, end_lat, end_lon: Tọa độ điểm đầu/cuối
    
    Returns:
        dict: {
            'route_geometry': List of [lat, lon] (đường thẳng)
            'distance_km': Khoảng cách (km)
            'duration_minutes': Thời gian ước lượng
            'is_simulation': True (đánh dấu là mô phỏng)
        }
    
    Example:
        >>> route = calculate_route_simple(10.762622, 106.660172, 10.850002, 106.771482)
        >>> print(f"⚠️  SIMULATION: {route['distance_km']}km")
    """
    # Tính khoảng cách đường chim bay
    distance_km = haversine_distance(start_lat, start_lon, end_lat, end_lon)
    
    # Tạo đường thẳng với 10 điểm trung gian
    num_points = 10
    route_points = []
    
    for i in range(num_points + 1):
        t = i / num_points  # Tỷ lệ từ 0 đến 1
        lat = start_lat + t * (end_lat - start_lat)
        lon = start_lon + t * (end_lon - start_lon)
        route_points.append([round(lat, 6), round(lon, 6)])
    
    # Ước lượng thời gian (giả định tốc độ trung bình 30 km/h trong thành phố)
    # Thực tế: route có thể dài hơn đường chim bay 1.3-1.5 lần
    estimated_route_km = distance_km * 1.4
    avg_speed_kmh = 30.0
    duration_minutes = (estimated_route_km / avg_speed_kmh) * 60.0
    
    return {
        'route_geometry': route_points,
        'route_geometry_lonlat': [[lon, lat] for lat, lon in route_points],
        'distance_km': round(estimated_route_km, 2),
        'distance_meters': round(estimated_route_km * 1000, 1),
        'duration_minutes': round(duration_minutes, 1),
        'duration_seconds': round(duration_minutes * 60, 1),
        'is_simulation': True,
        'warning': 'Đây là route MÔ PHỎNG, không phải đường đi thực tế!'
    }


# =============================================================================
# 5. HELPER FUNCTIONS - HÀM HỖ TRỢ
# =============================================================================

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Kiểm tra tọa độ có hợp lệ không.
    
    Args:
        lat (float): Vĩ độ
        lon (float): Kinh độ
    
    Returns:
        bool: True nếu hợp lệ
    
    Valid ranges:
        - Latitude: -90 to +90
        - Longitude: -180 to +180
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính bearing (hướng) từ điểm 1 đến điểm 2 (degrees).
    
    Bearing:
    --------
    - 0°: Bắc (North)
    - 90°: Đông (East)
    - 180°: Nam (South)
    - 270°: Tây (West)
    
    Công thức:
    ----------
    θ = atan2(sin(Δλ) × cos(φ2), cos(φ1) × sin(φ2) − sin(φ1) × cos(φ2) × cos(Δλ))
    
    Args:
        lat1, lon1, lat2, lon2: Tọa độ 2 điểm
    
    Returns:
        float: Bearing (0-360 degrees)
    
    Example:
        >>> bearing = get_bearing(10.762622, 106.660172, 10.850002, 106.771482)
        >>> print(f"Hướng: {bearing:.1f}°")  # Output: ~48.3° (Đông Bắc)
    """
    lat1_rad = lat1 * DEGREES_TO_RADIANS
    lat2_rad = lat2 * DEGREES_TO_RADIANS
    dlon_rad = (lon2 - lon1) * DEGREES_TO_RADIANS
    
    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad) -
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    )
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = bearing_rad / DEGREES_TO_RADIANS
    
    # Chuyển từ -180~180 sang 0~360
    return (bearing_deg + 360.0) % 360.0


def get_direction_name(bearing: float) -> str:
    """
    Chuyển bearing thành tên hướng (Bắc, Đông Bắc, Đông...).
    
    Args:
        bearing (float): Bearing (0-360 degrees)
    
    Returns:
        str: Tên hướng
    
    Example:
        >>> direction = get_direction_name(45.0)
        >>> print(direction)  # Output: "Đông Bắc"
    """
    directions = [
        "Bắc", "Đông Bắc", "Đông", "Đông Nam",
        "Nam", "Tây Nam", "Tây", "Tây Bắc"
    ]
    index = round(bearing / 45.0) % 8
    return directions[index]


def format_distance(distance_km: float) -> str:
    """
    Format khoảng cách thành string dễ đọc.
    
    Args:
        distance_km (float): Khoảng cách (km)
    
    Returns:
        str: Formatted string
    
    Example:
        >>> format_distance(0.5)
        "500m"
        >>> format_distance(5.3)
        "5.3km"
    """
    if distance_km < 1.0:
        return f"{int(distance_km * 1000)}m"
    return f"{distance_km:.1f}km"


# =============================================================================
# 6. BATCH OPERATIONS - XỬ LÝ HÀNG LOẠT
# =============================================================================

def find_nearest_parking(
    parking_queryset: QuerySet,
    center_lat: float,
    center_lon: float,
    max_radius_km: float = 50.0,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Tìm bãi đỗ xe GẦN NHẤT từ điểm trung tâm.
    
    Args:
        parking_queryset: Django QuerySet
        center_lat, center_lon: Tọa độ trung tâm
        max_radius_km: Bán kính tìm kiếm tối đa (default: 50km)
        **kwargs: Các tham số bổ sung cho find_nearby_parkings()
    
    Returns:
        dict hoặc None: Thông tin bãi đỗ gần nhất, hoặc None nếu không tìm thấy
    
    Example:
        >>> nearest = find_nearest_parking(
        ...     Parking.objects.all(),
        ...     10.762622, 106.660172,
        ...     only_available=True
        ... )
        >>> if nearest:
        ...     print(f"Gần nhất: {nearest['name']} - {nearest['distance_km']}km")
    """
    parkings = find_nearby_parkings(
        parking_queryset,
        center_lat,
        center_lon,
        max_radius_km,
        sort_by_distance=True,
        **kwargs
    )
    
    return parkings[0] if parkings else None


def find_parkings_in_area(
    parking_queryset: QuerySet,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float
) -> QuerySet:
    """
    Tìm tất cả bãi đỗ xe trong một vùng (bounding box).
    
    Use case:
    ---------
    - Hiển thị bãi đỗ trong viewport của bản đồ
    - Export dữ liệu theo khu vực
    - Thống kê theo vùng
    
    Args:
        parking_queryset: Django QuerySet
        min_lat, max_lat, min_lon, max_lon: Tọa độ 4 góc của vùng
    
    Returns:
        QuerySet: Các bãi đỗ trong vùng
    
    Example:
        >>> # Tất cả bãi trong Quận 1
        >>> parkings = find_parkings_in_area(
        ...     Parking.objects.all(),
        ...     10.760, 10.800,  # lat range
        ...     106.650, 106.690  # lon range
        ... )
    """
    return parking_queryset.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lon,
        longitude__lte=max_lon
    )


# =============================================================================
# 7. EXPORT FUNCTIONS - XUẤT DỮ LIỆU GIS
# =============================================================================

def export_parkings_geojson(parking_queryset: QuerySet) -> Dict[str, Any]:
    """
    Xuất dữ liệu bãi đỗ xe sang định dạng GeoJSON.
    
    GeoJSON Format:
    ---------------
    {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {...}
        }]
    }
    
    Args:
        parking_queryset: Django QuerySet
    
    Returns:
        dict: GeoJSON FeatureCollection
    
    Example:
        >>> geojson = export_parkings_geojson(Parking.objects.filter(is_active=True))
        >>> # Lưu file
        >>> with open('parkings.geojson', 'w') as f:
        ...     json.dump(geojson, f)
    
    Use cases:
        - Import vào QGIS, ArcGIS
        - Hiển thị trên Leaflet, Mapbox
        - Chia sẻ dữ liệu GIS
    """
    features = []
    
    for parking in parking_queryset.select_related('parking_type', 'khu_vuc'):
        status = parking.get_status()
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(parking.longitude), float(parking.latitude)]
            },
            "properties": {
                "id": parking.id,
                "name": parking.name,
                "parking_type": parking.parking_type.name,
                "khu_vuc": parking.khu_vuc.name,
                "available_slots": parking.available_slots,
                "total_slots": parking.total_slots,
                "capacity_percent": parking.get_capacity_percent(),
                "status": status.name if status else None,
                "status_color": status.color_code if status else None,
                "address": parking.address or '',
                "is_active": parking.is_active,
                "is_24h": parking.is_24h,
                "has_security": parking.has_security,
                "has_camera": parking.has_camera,
                "has_ev_charging": parking.has_ev_charging,
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }