from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import IntroductionPage

import random
import requests


from .auth_utils import is_manager_user
from .forms import ParkingRegistrationRequestForm, PublicLoginForm, PublicRegisterForm
from .models import ActivityLog, Area, OtpCode, ParkingLot, ParkingPrice, ParkingRegistrationRequest, ParkingUser
from .utils.gis import find_nearest_parking, haversine_distance
from .utils.email import send_registration_request_received_email, send_otp_email


def custom_not_found(request, exception):
    manager_prefix = f"/{settings.MANAGER_URL_PREFIX.strip('/')}/"
    template_name = "parking/manager/404.html" if request.path_info.startswith(manager_prefix) else "404.html"
    return render(request, template_name, status=404)


def preview_404(request):
    """Xem trước trang 404 khi DEBUG=True. Xóa URL này trước khi lên production."""
    which = request.GET.get("type", "public")
    if which == "manager":
        return render(request, "parking/manager/404.html", status=200)
    return render(request, "parking/404.html", status=200)


def public_login(request):
    if request.user.is_authenticated:
        if is_manager_user(request.user):
            return redirect("manager_dashboard")
        return redirect("home")

    form = PublicLoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
            return redirect(next_url)
        if is_manager_user(user):
            return redirect("manager_dashboard")
        return redirect("home")

    return render(request, "parking/auth/login.html", {"form": form})


def public_register(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = PublicRegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        # Lưu data vào session, chưa tạo user
        request.session["pending_registration"] = {
            "username": form.cleaned_data["username"],
            "email": form.cleaned_data["email"],
            "first_name": form.cleaned_data["first_name"],
            "password": form.cleaned_data["password1"],
        }
        # Tạo OTP 6 số
        otp_code = f"{random.randint(0, 999999):06d}"
        OtpCode.objects.filter(email=form.cleaned_data["email"], is_used=False).update(is_used=True)
        OtpCode.objects.create(
            email=form.cleaned_data["email"],
            code=otp_code,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        send_otp_email(form.cleaned_data["email"], otp_code)
        return redirect("verify_otp")

    return render(request, "parking/auth/register.html", {"form": form})


def verify_otp(request):
    if request.user.is_authenticated:
        return redirect("home")

    pending = request.session.get("pending_registration")
    if not pending:
        return redirect("register")

    error = None

    if request.method == "POST":
        action = request.POST.get("action", "verify")

        if action == "resend":
            otp_code = f"{random.randint(0, 999999):06d}"
            OtpCode.objects.filter(email=pending["email"], is_used=False).update(is_used=True)
            OtpCode.objects.create(
                email=pending["email"],
                code=otp_code,
                expires_at=timezone.now() + timezone.timedelta(minutes=10),
            )
            send_otp_email(pending["email"], otp_code)
            messages.success(request, "Đã gửi lại mã OTP. Vui lòng kiểm tra email.")
            return redirect("verify_otp")

        entered = (request.POST.get("otp_code") or "").strip()
        otp = OtpCode.objects.filter(
            email=pending["email"],
            code=entered,
            is_used=False,
        ).order_by("-created_at").first()

        if not otp:
            error = "Mã OTP không đúng. Vui lòng kiểm tra lại."
        elif otp.is_expired():
            error = "Mã OTP đã hết hạn. Hãy nhấn Gửi lại để nhận mã mới."
        else:
            otp.is_used = True
            otp.save(update_fields=["is_used"])

            if User.objects.filter(username=pending["username"]).exists():
                error = "Tên đăng nhập đã tồn tại. Vui lòng quay lại đăng ký."
            else:
                user = User.objects.create_user(
                    username=pending["username"],
                    email=pending["email"],
                    password=pending["password"],
                    first_name=pending["first_name"],
                )
                del request.session["pending_registration"]
                login(request, user)
                messages.success(request, "Đăng ký thành công. Chào mừng bạn!")
                return redirect("home")

    return render(request, "parking/auth/verify_otp.html", {
        "email": pending["email"],
        "error": error,
    })


def public_logout(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất.")
    return redirect("home")


@login_required(login_url="login")
def parking_registration_create(request):
    form = ParkingRegistrationRequestForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            registration = form.save(commit=False)
            registration.created_by = request.user
            registration.save()
            ActivityLog.objects.create(
                action=f"Đơn đăng ký mới {registration.full_name} cho bãi {registration.parking_lot.name}",
                type="system",
            )
        mail_result = send_registration_request_received_email(registration)
        if mail_result.get("skipped"):
            messages.success(
                request,
                "Đã gửi đơn đăng ký gửi xe thành công.",
            )
        elif mail_result.get("live_sent") and mail_result.get("sandbox_sent"):
            messages.success(
                request,
                "Đã gửi đơn đăng ký gửi xe. Email xác nhận đã được gửi đến người đăng ký và đồng thời lưu vào Mailtrap Sandbox.",
            )
        elif mail_result.get("ok"):
            messages.warning(
                request,
                "Đã gửi đơn đăng ký gửi xe. Tuy nhiên email mới chỉ gửi được một phần, hãy kiểm tra cấu hình Mailtrap nếu bạn cần đồng bộ cả live và sandbox.",
            )
        else:
            messages.warning(
                request,
                "Đã lưu đơn đăng ký gửi xe, nhưng chưa gửi được email thông báo. Hãy kiểm tra cấu hình Mailtrap.",
            )
        return redirect("parking_registration_create")

    return render(
        request,
        "parking/parking_registration_form.html",
        {"form": form},
    )


@login_required(login_url="login")
def parking_registration_history(request):
    registrations = ParkingRegistrationRequest.objects.select_related("parking_lot").filter(
        created_by=request.user
    ).order_by("-created_at")

    return render(
        request,
        "parking/parking_registration_history.html",
        {"registrations": registrations},
    )


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
    }

    return render(request, "parking/home.html", context)


def map_view(request):
    areas = Area.objects.filter(is_deleted=False)
    return render(request, "parking/map.html", {"areas": areas})


def parking_list(request):
    parkings = ParkingLot.objects.filter(is_deleted=False).prefetch_related("images")
    parking_items = []
    total_capacity = 0
    total_available = 0
    active_count = 0

    for p in parkings:
        available = p.available_slots()
        used = p.used_slots()

        total_capacity += p.capacity
        total_available += available
        if p.is_active:
            active_count += 1

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
                "short_description": p.short_description,
                "long_description": p.long_description,
                "primary_image": p.primary_image(),
            }
        )

    context = {
        "parking_list": parking_items,
        "parking_total": len(parking_items),
        "parking_active": active_count,
        "parking_capacity": total_capacity,
        "parking_available": total_available,
        "parking_used": max(total_capacity - total_available, 0),
    }

    return render(request, "parking/parking_list.html", context)


def parking_available(request):
    parking_lots = [
        p
        for p in ParkingLot.objects.filter(is_active=True, is_deleted=False)
        if p.available_slots() > 0
    ]
    return render(request, "parking/parking_available.html", {"parking_lots": parking_lots})


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
    parking = get_object_or_404(ParkingLot.objects.prefetch_related("images"), id=id, is_deleted=False)

    available = parking.available_slots()
    used = parking.capacity - available
    price_list = list(ParkingPrice.objects.filter(parking_lot=parking).order_by("vehicle_type"))

    context = {
        "parking": parking,
        "available": available,
        "used": used,
        "is_full": available <= 0,
        "price_list": price_list,
        "images": parking.images.all(),
        "primary_image": parking.primary_image(),
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
    for p in ParkingLot.objects.filter(is_deleted=False):
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
        return JsonResponse({"error": "Thiếu lat/lon"}, status=400)

    parkings = ParkingLot.objects.filter(is_deleted=False, is_active=True)
    nearest = find_nearest_parking(parkings, lat, lon, only_available=True)
    return JsonResponse(nearest or {"message": "Không có bãi đỗ phù hợp"})


def api_route(request):
    try:
        start_lat = float(request.GET.get("start_lat"))
        start_lon = float(request.GET.get("start_lon"))
        end_lat = float(request.GET.get("end_lat"))
        end_lon = float(request.GET.get("end_lon"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Thiếu tọa độ"}, status=400)

    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except requests.RequestException:
        return JsonResponse({"error": "Không kết nối được dịch vụ dẫn đường"}, status=502)

    if "routes" not in data:
        return JsonResponse({"error": "Không tìm được đường đi"}, status=400)

    return JsonResponse(data["routes"][0]["geometry"])


def search_by_phone(request):
    phone = request.GET.get("phone", "").strip()

    if not phone:
        return redirect("home")

    user = ParkingUser.objects.filter(phone=phone, is_deleted=False).first()

    if not user:
        return render(request, "parking/search.html", {"error": "Không tìm thấy khách hàng"})

    return redirect("parking_user_detail", user.id)


def parking_user_detail(request, id):
    user = get_object_or_404(ParkingUser, id=id, is_deleted=False)
    return render(request, "parking/customer_detail.html", {"user": user})


def checkout_vehicle(request, user_id):
    user = get_object_or_404(ParkingUser, id=user_id, is_deleted=False)

    if user.is_active:
        user.exit_parking()
        messages.success(request, "Xe đã được check-out thành công")

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
        message = "Email đã được xác thực hoặc liên kết không hợp lệ."
    elif token != parking_user.email_verification_token:
        status = "error"
        message = "Liên kết xác thực không hợp lệ hoặc đã hết hạn."
    else:
        parking_user.email_verified = True
        parking_user.email_verification_token = None
        parking_user.email_verification_sent_at = None
        parking_user.save(
            update_fields=[
                "email_verified",
                "email_verification_token",
                "email_verification_sent_at",
            ]
        )
        status = "success"
        message = "Xác thực email thành công."

    return render(
        request,
        "parking/verify_email_result.html",
        {
            "status": status,
            "message": message,
            "parking_user": parking_user,
        },
    )


def custom_page_not_found(request, exception=None):
    template_name = "parking/manager/404.html" if request.path.startswith("/manager/") else "parking/404.html"
    return render(request, template_name, status=404)


def about(request):
    return render(request, "parking/about.html")

from .models import IntroductionPage

def gioi_thieu(request):

    intro = IntroductionPage.objects.first()

    return render(request, 'parking/about.html', {
        'intro': intro
    })