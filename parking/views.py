from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import ParkingLot, Area, ActivityLog, ParkingUser
from .utils.gis import (
    haversine_distance,
    find_nearest_parking,
    find_nearby_parkings,
    calculate_route_osrm,
    calculate_route_simple
)


# ================== DASHBOARD ==================
def home(request):
    parkings = ParkingLot.objects.all()
    total_available = 0
    total_revenue = 0
    parking_data = []

    for p in parkings:
        available = p.available_slots
        used = p.capacity - available if p.capacity > 0 else 0
        percent = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        vehicle_count = ParkingUser.objects.filter(
            parking_lot=p, is_active=True
        ).count()

        revenue = vehicle_count * p.price_per_hour * 2
        total_revenue += revenue
        total_available += available

        parking_data.append({
            "obj": p,
            "available": available,
            "used": used,
            "percent": percent,
            "is_full": p.is_full()
        })

    context = {
        "total_parking": parkings.count(),
        "total_available": total_available,
        "revenue": total_revenue,
        "active_areas": Area.objects.count(),
        "parking_data": parking_data,
        "activities": ActivityLog.objects.order_by("-time")[:5]
    }
    return render(request, "parking/home.html", context)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import ParkingLot, Area, ActivityLog, ParkingUser
from .utils.gis import (
    haversine_distance,
    find_nearest_parking,
    find_nearby_parkings,
    calculate_route_osrm,
    calculate_route_simple
)

# ================== REVENUE ==================
def revenue_view(request):
    parkings = ParkingLot.objects.all()
    data = []
    total_revenue = 0

    for p in parkings:
        active_vehicles = ParkingUser.objects.filter(
            parking_lot=p,
            is_active=True
        ).count()

        revenue = active_vehicles * p.price_per_hour * 2
        total_revenue += revenue

        data.append({
            "parking": p,
            "active_vehicles": active_vehicles,
            "price_per_hour": p.price_per_hour,
            "revenue": revenue
        })

    return render(request, "parking/revenue.html", {
        "total_revenue": total_revenue,
        "revenue_data": data
    })


# ================== DASHBOARD ==================
def home(request):
    parkings = ParkingLot.objects.all()
    total_available = 0
    total_revenue = 0
    parking_data = []

    for p in parkings:
        available = p.available_slots
        used = p.capacity - available if p.capacity > 0 else 0
        percent = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        vehicle_count = ParkingUser.objects.filter(
            parking_lot=p, is_active=True
        ).count()

        revenue = vehicle_count * p.price_per_hour * 2
        total_revenue += revenue
        total_available += available

        parking_data.append({
            "obj": p,
            "available": available,
            "used": used,
            "percent": percent,
            "is_full": p.is_full()
        })

    context = {
        "total_parking": parkings.count(),
        "total_available": total_available,
        "revenue": total_revenue,
        "active_areas": Area.objects.count(),
        "parking_data": parking_data,
        "activities": ActivityLog.objects.order_by("-time")[:5]
    }
    return render(request, "parking/home.html", context)


# ================== MAP ==================
def map_view(request):
    return render(request, "parking/map.html", {
        "areas": Area.objects.all()
    })


# ================== PARKING LIST ==================
def parking_list(request):
    parkings = ParkingLot.objects.select_related("area")
    data = []

    for p in parkings:
        used = p.capacity - p.available_slots
        percent_used = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        data.append({
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "area": p.area,
            "capacity": p.capacity,
            "available": p.available_slots,
            "percent_used": percent_used,
            "is_active": p.is_active
        })

    return render(request, "parking/parking_list.html", {
        "parking_list": data
    })


# ================== AVAILABLE PARKING ==================
def available_parking(request):
    parkings = ParkingLot.objects.filter(
        is_active=True, available_slots__gt=0
    )
    return render(request, "parking/available.html", {
        "parking_lots": parkings
    })


# ================== PARKING DETAIL ==================
def parking_detail(request, id):
    parking = get_object_or_404(ParkingLot, id=id)
    return render(request, "parking/parking_detail.html", {
        "parking": parking
    })


# ================== AREAS ==================
def areas_view(request):
    data = []
    for area in Area.objects.all():
        parkings = ParkingLot.objects.filter(area=area)
        data.append({
            "obj": area,
            "parking_count": parkings.count(),
            "is_active": parkings.filter(is_active=True).exists()
        })

    return render(request, "parking/areas.html", {
        "areas_data": data
    })


# ================== ACTIVITY LOG ==================
def activity_log_view(request):
    return render(request, "parking/activity_log.html", {
        "logs": ActivityLog.objects.order_by("-time")
    })


# ================== GIS API: FIND NEAREST ==================
@require_GET
def api_find_nearest_parking(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu lat/lon"}, status=400)

    result = find_nearest_parking(
        ParkingLot.objects.all(),
        lat,
        lon,
        only_available=True
    )

    if not result:
        return JsonResponse({"message": "Không có bãi đỗ phù hợp"})

    return JsonResponse(result, safe=False)


# ================== GIS API: NEARBY PARKINGS ==================
@require_GET
def api_nearby_parkings(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
        radius = float(request.GET.get("radius", 5))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Tham số không hợp lệ"}, status=400)

    results = find_nearby_parkings(
        ParkingLot.objects.all(),
        lat,
        lon,
        radius,
        only_active=True,
        only_available=False
    )

    return JsonResponse(results, safe=False)


# ================== GIS API: ROUTE ==================
@require_GET
def api_route(request):
    try:
        start_lat = float(request.GET.get("start_lat"))
        start_lon = float(request.GET.get("start_lon"))
        end_lat = float(request.GET.get("end_lat"))
        end_lon = float(request.GET.get("end_lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu hoặc sai tọa độ"}, status=400)

    route = calculate_route_osrm(
        start_lat, start_lon, end_lat, end_lon
    )

    if not route:
        route = calculate_route_simple(
            start_lat, start_lon, end_lat, end_lon
        )

    return JsonResponse(route)


# ================== MAP ==================
def map_view(request):
    return render(request, "parking/map.html", {
        "areas": Area.objects.all()
    })


# ================== PARKING LIST ==================
def parking_list(request):
    parkings = ParkingLot.objects.select_related("area")
    data = []

    for p in parkings:
        used = p.capacity - p.available_slots
        percent_used = int((used / p.capacity) * 100) if p.capacity > 0 else 0

        data.append({
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "area": p.area,
            "capacity": p.capacity,
            "available": p.available_slots,
            "percent_used": percent_used,
            "is_active": p.is_active
        })

    return render(request, "parking/parking_list.html", {
        "parking_list": data
    })


# ================== AVAILABLE PARKING ==================
def available_parking(request):
    parkings = ParkingLot.objects.filter(
        is_active=True, available_slots__gt=0
    )
    return render(request, "parking/available.html", {
        "parking_lots": parkings
    })


# ================== PARKING DETAIL ==================
def parking_detail(request, id):
    parking = get_object_or_404(ParkingLot, id=id)
    return render(request, "parking/parking_detail.html", {
        "parking": parking
    })


# ================== AREAS ==================
def areas_view(request):
    data = []
    for area in Area.objects.all():
        parkings = ParkingLot.objects.filter(area=area)
        data.append({
            "obj": area,
            "parking_count": parkings.count(),
            "is_active": parkings.filter(is_active=True).exists()
        })

    return render(request, "parking/areas.html", {
        "areas_data": data
    })


# ================== ACTIVITY LOG ==================
def activity_log_view(request):
    return render(request, "parking/activity_log.html", {
        "logs": ActivityLog.objects.order_by("-time")
    })


# ================== GIS API: FIND NEAREST ==================
@require_GET
def api_find_nearest_parking(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu lat/lon"}, status=400)

    result = find_nearest_parking(
        ParkingLot.objects.all(),
        lat,
        lon,
        only_available=True
    )

    if not result:
        return JsonResponse({"message": "Không có bãi đỗ phù hợp"})

    return JsonResponse(result, safe=False)


# ================== GIS API: NEARBY PARKINGS ==================
@require_GET
def api_nearby_parkings(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
        radius = float(request.GET.get("radius", 5))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Tham số không hợp lệ"}, status=400)

    results = find_nearby_parkings(
        ParkingLot.objects.all(),
        lat,
        lon,
        radius,
        only_active=True,
        only_available=False
    )

    return JsonResponse(results, safe=False)


# ================== GIS API: ROUTE ==================
@require_GET
def api_route(request):
    try:
        start_lat = float(request.GET.get("start_lat"))
        start_lon = float(request.GET.get("start_lon"))
        end_lat = float(request.GET.get("end_lat"))
        end_lon = float(request.GET.get("end_lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu hoặc sai tọa độ"}, status=400)

    route = calculate_route_osrm(
        start_lat, start_lon, end_lat, end_lon
    )

    if not route:
        route = calculate_route_simple(
            start_lat, start_lon, end_lat, end_lon
        )

    return JsonResponse(route)

print(">>> views.py loaded")

# ================== PARKING BY STATUS ==================
@require_GET
def api_parking_by_status(request):
    """
    API lọc bãi đỗ theo trạng thái
    Params:
        - status_id
        - status_name
    """
    status_id = request.GET.get("status_id")
    status_name = request.GET.get("status")

    qs = ParkingLot.objects.select_related("status", "area")

    if status_id:
        qs = qs.filter(status_id=status_id)
    elif status_name:
        qs = qs.filter(status__name__iexact=status_name)

    data = []
    for p in qs:
        data.append({
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "area": p.area.name if p.area else None,
            "status": {
                "name": p.status.name if p.status else None,
                "color": p.status.color_code if p.status else None
            },
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
            "available_slots": p.available_slots,
            "capacity": p.capacity,
            "is_full": p.is_full(),
        })

    return JsonResponse({
        "count": len(data),
        "results": data
    })