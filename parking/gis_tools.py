# parking/gis_tools.py

import math

# -----------------------------
# TOOL 1: TÍNH KHOẢNG CÁCH (HAVERSINE)
# -----------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 điểm trên Trái Đất (km)
    """
    R = 6371  # Bán kính Trái Đất (km)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# -----------------------------
# TOOL 2: BÃI ĐỖ XE TRONG BÁN KÍNH
# -----------------------------
def parking_within_radius(center_lat, center_lng, radius_km, parking_list):
    """
    Input:
        center_lat, center_lng: vị trí người dùng
        radius_km: bán kính (km)
        parking_list: list các bãi đỗ (dict hoặc object)

    Output:
        list bãi đỗ xe trong bán kính
    """
    result = []

    for parking in parking_list:
        dist = haversine_distance(
            center_lat,
            center_lng,
            parking["lat"],
            parking["lng"]
        )

        if dist <= radius_km:
            parking_copy = parking.copy()
            parking_copy["distance_km"] = round(dist, 2)
            result.append(parking_copy)

    return result


# -----------------------------
# TOOL 3: TÌM ĐƯỜNG TỐI ƯU (GIẢ LẬP)
# -----------------------------
def find_optimal_route(start, end):
    """
    Tool mô phỏng tìm đường
    Input:
        start: (lat, lng)
        end: (lat, lng)

    Output:
        danh sách tọa độ mô phỏng tuyến đường
    """
    return [
        start,
        (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2
        ),
        end
    ]


# -----------------------------
# TOOL 4: PHÂN TÍCH HOTSPOT (MẬT ĐỘ)
# -----------------------------
def hotspot_analysis(parking_list):
    """
    Input:
        parking_list: danh sách bãi đỗ xe

    Output:
        danh sách điểm để vẽ heatmap
    """
    heatmap_points = []

    for p in parking_list:
        heatmap_points.append([p["lat"], p["lng"], 1])

    return heatmap_points
