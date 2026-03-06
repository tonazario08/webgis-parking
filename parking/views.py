from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.utils import timezone
import requests

from .models import ParkingLot, Area, ActivityLog, ParkingUser, ParkingPrice
from .utils.gis import haversine_distance, find_nearest_parking


def home(request):
    parkings = ParkingLot.objects.all()
    parking_data = []
    total_available = 0
    total_revenue = 0

    active_users = ParkingUser.objects.filter(is_active=True)

    for p in parkings:
        available = p.available_slots()
        used = p.used_slots()
        percent = p.usage_percent()

        total_available += available

        revenue = 0
        users = active_users.filter(parking_lot=p)

        for u in users:
            try:
                price = ParkingPrice.objects.get(parking_lot=p, vehicle_type=u.vehicle_type)
                revenue += price.price_per_hour
            except ParkingPrice.DoesNotExist:
                pass

        total_revenue += revenue

        parking_data.append(
            {
                "obj": p,
                "available": available,
                "used": used,
                "percent": percent,
                "is_full": available == 0,
                "revenue": revenue,
            }
        )

    context = {
        "total_parking": parkings.count(),
        "total_available": total_available,
        "revenue": total_revenue,
        "active_areas": Area.objects.count(),
        "parking_data": parking_data,
        "activities": ActivityLog.objects.all()[:5],
    }

    return render(request, "parking/home.html", context)


def map_view(request):
    areas = Area.objects.all()
    return render(request, "parking/map.html", {"areas": areas})


def parking_list(request):
    parkings = ParkingLot.objects.all()
    parking_items = []

    for p in parkings:
        available = p.available_slots()
        used = p.used_slots()

        parking_items.append(
            {
                "id": p.id,
                "name": p.name,
                "address": p.address,
                "area": p.area,
                "is_active": p.is_active,
                "capacity": p.capacity,
                "available": available,
                "percent_used": p.usage_percent(),
                "used": used,
            }
        )

    return render(request, "parking/parking_list.html", {"parking_list": parking_items})


def parking_available(request):
    parking_lots = [p for p in ParkingLot.objects.filter(is_active=True) if p.available_slots() > 0]
    return render(request, "parking/parking_available.html", {"parking_lots": parking_lots})


def revenue_view(request):
    now = timezone.now()
    total_revenue = 0
    parking_data = []

    for lot in ParkingLot.objects.all():
        users = ParkingUser.objects.filter(
            parking_lot=lot,
            is_active=True,
            created_at__month=now.month,
            created_at__year=now.year,
        )

        lot_revenue = 0
        for u in users:
            price = ParkingPrice.objects.filter(parking_lot=lot, vehicle_type=u.vehicle_type).first()
            if price:
                lot_revenue += price.price_per_hour

        total_revenue += lot_revenue

        parking_data.append(
            {
                "name": lot.name,
                "month": f"{now.month}/{now.year}",
                "revenue": lot_revenue,
                "status": "Da quyet toan" if lot_revenue > 0 else "Chua doi soat",
            }
        )

    return render(request, "parking/revenue.html", {"total_revenue": total_revenue, "parking_data": parking_data})


def areas_view(request):
    data = []
    for a in Area.objects.all():
        parkings = ParkingLot.objects.filter(area=a)
        data.append(
            {
                "obj": a,
                "parking_count": parkings.count(),
                "is_active": parkings.filter(is_active=True).exists(),
            }
        )

    return render(request, "parking/areas.html", {"areas_data": data})


def parking_detail(request, id):
    parking = get_object_or_404(ParkingLot, id=id)

    available = parking.available_slots()
    used = parking.capacity - available

    context = {
        "parking": parking,
        "available": available,
        "used": used,
        "is_full": available <= 0,
    }

    return render(request, "parking/parking_detail.html", context)


def activity_log_view(request):
    logs = ActivityLog.objects.order_by("-created_at")
    return render(request, "parking/activity_log.html", {"logs": logs})


def nearest_parking_page(request):
    try:
        user_lat = float(request.GET.get("lat"))
        user_lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thieu toa do"}, status=400)

    results = []

    for p in ParkingLot.objects.filter(is_active=True):
        lat = p.latitude if p.latitude is not None else (p.area.latitude if p.area else None)
        lon = p.longitude if p.longitude is not None else (p.area.longitude if p.area else None)
        if lat is None or lon is None:
            continue

        distance = haversine_distance(user_lat, user_lon, lat, lon)
        results.append({"parking": p, "distance": round(distance, 2)})

    results.sort(key=lambda x: x["distance"])

    return render(request, "parking/parking_available.html", {"results": results})


@require_GET
def api_find_nearest_parking(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thieu lat/lon"}, status=400)

    nearest = find_nearest_parking(ParkingLot.objects.select_related("area").filter(is_active=True), lat, lon, only_available=True)
    return JsonResponse(nearest or {"message": "Khong co bai do phu hop"})


@require_GET
def api_route(request):
    try:
        start_lat = float(request.GET.get("start_lat"))
        start_lon = float(request.GET.get("start_lon"))
        end_lat = float(request.GET.get("end_lat"))
        end_lon = float(request.GET.get("end_lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thieu toa do"}, status=400)

    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except requests.RequestException:
        return JsonResponse({"error": "Khong ket noi duoc dich vu dan duong"}, status=502)

    if "routes" not in data:
        return JsonResponse({"error": "Khong tim duoc duong di"}, status=400)

    return JsonResponse(data["routes"][0]["geometry"])


def search_by_phone(request):
    phone = request.GET.get("phone", "").strip()

    if not phone:
        return redirect("home")

    user = ParkingUser.objects.filter(phone=phone).first()

    if not user:
        return render(request, "parking/search.html", {"error": "Khong tim thay khach hang"})

    return redirect("parking_user_detail", user.id)


def parking_user_detail(request, id):
    user = get_object_or_404(ParkingUser, id=id)
    return render(request, "parking/customer_detail.html", {"user": user})


def checkout_vehicle(request, user_id):
    user = get_object_or_404(ParkingUser, id=user_id)

    if user.is_active:
        user.exit_parking()
        messages.success(request, "Xe da duoc check-out thanh cong")

    return redirect("customer_detail", user_id=user.id)


def parking_map_data(request):
    parkings = ParkingLot.objects.select_related("area")

    data = []
    for p in parkings:
        lat = p.latitude
        lng = p.longitude
        if (lat is None or lng is None) and p.area:
            lat = p.area.latitude
            lng = p.area.longitude
        if lat is None or lng is None:
            continue

        data.append(
            {
                "id": p.id,
                "name": p.name,
                "lat": float(lat),
                "lng": float(lng),
                "district": p.district or (p.area.name if p.area else ""),
                "address": p.address,
                "capacity": p.capacity,
                "available_slots": p.available_slots(),
            }
        )

    return JsonResponse(data, safe=False)
