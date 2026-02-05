from django.shortcuts import render, get_object_or_404
from .models import ParkingLot, Area, ActivityLog, ParkingUser
from .utils.gis import haversine_distance
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .utils.gis import find_nearest_parking
# ================== DASHBOARD ==================
def home(request):
    parkings = ParkingLot.objects.all()

    parking_data = []
    total_available = 0
    total_revenue = 0

    for p in parkings:
        available = p.available_slots()          # GỌI HÀM
        used = p.capacity - available if p.capacity else 0
        percent = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        total_available += available

        vehicle_count = ParkingUser.objects.filter(
            parking_lot=p,
            is_active=True
        ).count()
        total_revenue += vehicle_count * p.price_per_hour * 2

        parking_data.append({
            'obj': p,
            'available': available,
            'used': used,
            'percent': percent,
            'is_full': available == 0
        })

    context = {
        'total_parking': parkings.count(),
        'total_available': total_available,
        'revenue': total_revenue,
        'active_areas': Area.objects.count(),
        'parking_data': parking_data,   # 👈 DỮ LIỆU ĐÚNG
        'activities': ActivityLog.objects.all()[:5]
    }

    return render(request, 'parking/home.html', context)



# ================== MAP ==================
def map_view(request):
    areas = Area.objects.all()
    return render(request, 'parking/map.html', {
        'areas': areas
    })


# ================== PARKING LIST ==================
def parking_list(request):
    parkings = ParkingLot.objects.all()
    parking_list = []

    for p in parkings:
        available = p.available_slots()
        used = p.capacity - available
        percent_used = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        parking_list.append({
            'id': p.id,
            'name': p.name,
            'address': p.address,
            'area': p.area,
            'is_active': p.is_active,
            'capacity': p.capacity,
            'available': available,
            'percent_used': percent_used
        })

    return render(request, 'parking/parking_list.html', {
        'parking_list': parking_list
    })


# ================== AVAILABLE PARKING ==================
def available_parking(request):
    parking_lots = [
        p for p in ParkingLot.objects.filter(is_active=True)
        if p.available_slots() > 0
    ]

    return render(request, 'parking/available.html', {
        'parking_lots': parking_lots
    })


# ================== REVENUE ==================
def revenue_view(request):
    total_revenue = 0
    parking_data = []

    parking_lots = ParkingLot.objects.all()

    for p in parking_lots:
        vehicle_count = ParkingUser.objects.filter(
            parking_lot=p
        ).count()

        revenue = vehicle_count * p.price_per_hour * 2
        total_revenue += revenue

        parking_data.append({
            'name': p.name,
            'month': '01/2026',
            'revenue': revenue,
            'status': 'Đã quyết toán' if revenue > 0 else 'Chưa đối soát'
        })

    context = {
        'total_revenue': total_revenue,
        'parking_data': parking_data
    }
    return render(request, 'parking/revenue.html', context)



# ================== AREAS ==================
def areas_view(request):
    areas = Area.objects.all()
    data = []

    for a in areas:
        parkings = ParkingLot.objects.filter(area=a)

        parking_count = parkings.count()

        # Khu vực hoạt động nếu có ít nhất 1 bãi xe đang active
        is_active = parkings.filter(is_active=True).exists()

        data.append({
            'obj': a,
            'parking_count': parking_count,
            'is_active': is_active
        })

    return render(request, 'parking/areas.html', {
        'areas_data': data
    })




# ================== PARKING DETAIL ==================
def parking_detail(request, id):
    parking = get_object_or_404(ParkingLot, id=id)
    return render(request, 'parking/parking_detail.html', {
        'parking': parking
    })


# ================== ACTIVITY LOG ==================
def activity_log_view(request):
    logs = ActivityLog.objects.order_by('-time')
    return render(request, 'parking/activity_log.html', {
        'logs': logs
    })
def find_nearest_parking(request):
    user_lat = float(request.GET.get('lat'))
    user_lon = float(request.GET.get('lon'))

    parkings = ParkingLot.objects.filter(is_active=True)

    results = []

    for p in parkings:
        distance = haversine_distance(
            user_lat, user_lon,
            p.latitude, p.longitude
        )

        results.append({
            'parking': p,
            'distance': round(distance, 2)
        })

    results.sort(key=lambda x: x['distance'])

    return render(request, 'parking/available.html', {
        'results': results
    })
@require_GET
def api_find_nearest_parking(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu lat/lon"}, status=400)

    nearest = find_nearest_parking(
        ParkingLot.objects.all(),
        lat, lon,
        only_available=True
    )

    if not nearest:
        return JsonResponse({"message": "Không có bãi đỗ phù hợp"})

    return JsonResponse(nearest)


@require_GET
def api_route(request):
    try:
        start_lat = request.GET.get("start_lat")
        start_lon = request.GET.get("start_lon")
        end_lat = request.GET.get("end_lat")
        end_lon = request.GET.get("end_lon")
    except:
        return JsonResponse({"error": "Thiếu tọa độ"}, status=400)

    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    res = requests.get(url)
    data = res.json()

    if "routes" not in data:
        return JsonResponse({"error": "Không tìm được đường đi"}, status=400)

    return JsonResponse(data["routes"][0]["geometry"])