from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
import requests

from .models import ParkingLot, Area, ActivityLog, ParkingUser, ParkingPrice
from .utils.gis import haversine_distance, find_nearest_parking


def home(request):
    parkings_all = list(ParkingLot.objects.filter(is_deleted=False).order_by("id"))
    parking_stats = {}
    total_available = 0
    total_revenue = 0

    active_users = ParkingUser.objects.filter(is_active=True, is_deleted=False)

    for p in parkings_all:
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
        parking_stats[p.id] = {
            "available": available,
            "used": used,
            "percent": percent,
            "revenue": revenue,
        }

    paginator = Paginator(parkings_all, 5)
    page_number = request.GET.get("page")
    parkings_page = paginator.get_page(page_number)

    parking_data = []
    for p in parkings_page:
        stats = parking_stats.get(p.id, {})
        parking_data.append(
            {
                "obj": p,
                "available": stats.get("available", 0),
                "used": stats.get("used", 0),
                "percent": stats.get("percent", 0),
                "is_full": stats.get("available", 0) == 0,
                "revenue": stats.get("revenue", 0),
            }
        )

    context = {
        "total_parking": len(parkings_all),
        "total_available": total_available,
        "revenue": total_revenue,
        "active_areas": Area.objects.filter(is_deleted=False).count(),
        "parking_data": parking_data,
        "parking_page": parkings_page,
        "activities": ActivityLog.objects.all()[:5],
    }

    return render(request, "parking/home.html", context)


def map_view(request):
    areas = Area.objects.filter(is_deleted=False)
    return render(request, "parking/map.html", {"areas": areas})


def parking_list(request):
    parkings = ParkingLot.objects.filter(is_deleted=False)
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
    parking_lots = [p for p in ParkingLot.objects.filter(is_active=True, is_deleted=False) if p.available_slots() > 0]
    return render(request, "parking/parking_available.html", {"parking_lots": parking_lots})


def revenue_view(request):
    now = timezone.now()
    total_revenue = 0
    parking_data = []

    for lot in ParkingLot.objects.filter(is_deleted=False):
        users = ParkingUser.objects.filter(
            parking_lot=lot,
            is_active=True,
            is_deleted=False,
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
    for a in Area.objects.filter(is_deleted=False):
        parkings = ParkingLot.objects.filter(area=a, is_deleted=False)
        data.append(
            {
                "obj": a,
                "parking_count": parkings.count(),
                "is_active": parkings.filter(is_active=True).exists(),
            }
        )

    return render(request, "parking/areas.html", {"areas_data": data})


def parking_detail(request, id):
    parking = get_object_or_404(ParkingLot, id=id, is_deleted=False)

    available = parking.available_slots()
    used = parking.capacity - available
    price_list = list(ParkingPrice.objects.filter(parking_lot=parking).order_by("vehicle_type"))

    context = {
        "parking": parking,
        "available": available,
        "used": used,
        "is_full": available <= 0,
        "price_list": price_list,
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

    for p in ParkingLot.objects.filter(is_active=True, is_deleted=False):
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

    nearest = find_nearest_parking(ParkingLot.objects.select_related("area").filter(is_active=True, is_deleted=False), lat, lon, only_available=True)
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

    user = ParkingUser.objects.filter(phone=phone, is_deleted=False).first()

    if not user:
        return render(request, "parking/search.html", {"error": "Khong tim thay khach hang"})

    return redirect("parking_user_detail", user.id)


def parking_user_detail(request, id):
    user = get_object_or_404(ParkingUser, id=id, is_deleted=False)
    return render(request, "parking/customer_detail.html", {"user": user})


def checkout_vehicle(request, user_id):
    user = get_object_or_404(ParkingUser, id=user_id, is_deleted=False)

    if user.is_active:
        user.exit_parking()
        messages.success(request, "Xe da duoc check-out thanh cong")

    return redirect("customer_detail", user_id=user.id)


def parking_map_data(request):
    parkings = ParkingLot.objects.select_related("area").filter(is_deleted=False)

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


def verify_parking_user_email(request, user_id, token):
    parking_user = get_object_or_404(ParkingUser, pk=user_id, is_deleted=False)

    if not parking_user.email_verification_token:
        status = "error"
        message = "Email da duoc xac thuc hoac lien ket khong hop le."
    elif token != parking_user.email_verification_token:
        status = "error"
        message = "Lien ket xac thuc khong hop le hoac da het han."
    else:
        parking_user.email_verified = True
        parking_user.email_verification_token = None
        parking_user.email_verification_sent_at = None
        parking_user.save(update_fields=[
            "email_verified",
            "email_verification_token",
            "email_verification_sent_at",
        ])
        status = "success"
        message = "Xac thuc email thanh cong."

    return render(
        request,
        "parking/verify_email_result.html",
        {
            "status": status,
            "message": message,
            "parking_user": parking_user,
        },
    )
