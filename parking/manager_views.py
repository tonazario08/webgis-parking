from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import ActivityLog, Area, ParkingLot, ParkingPrice, ParkingUser


MANAGER_MODELS = {
    "areas": {
        "model": Area,
        "title": "Khu vuc",
        "fields": ["name", "description", "latitude", "longitude"],
        "columns": ["name", "description", "latitude", "longitude"],
    },
    "parkings": {
        "model": ParkingLot,
        "title": "Bai do xe",
        "fields": [
            "name",
            "address",
            "area",
            "latitude",
            "longitude",
            "district",
            "capacity",
            "is_active",
            "revenue",
        ],
        "columns": [
            "name",
            "area",
            "district",
            "capacity",
            "used_slots",
            "available_slots",
            "is_active",
            "revenue",
        ],
    },
    "users": {
        "model": ParkingUser,
        "title": "Nguoi gui xe",
        "fields": [
            "full_name",
            "phone",
            "email",
            "address",
            "license_plate",
            "vehicle_type",
            "parking_lot",
            "is_active",
        ],
        "columns": [
            "full_name",
            "phone",
            "license_plate",
            "vehicle_type",
            "parking_lot",
            "is_active",
            "created_at",
        ],
    },
    "prices": {
        "model": ParkingPrice,
        "title": "Bang gia",
        "fields": ["parking_lot", "vehicle_type", "price_per_hour"],
        "columns": ["parking_lot", "vehicle_type", "price_per_hour"],
    },
    "logs": {
        "model": ActivityLog,
        "title": "Nhat ky hoat dong",
        "fields": [],
        "columns": ["action", "type", "user", "created_at"],
        "readonly": True,
    },
}


def _is_manager(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _style_form(form):
    for field in form.fields.values():
        current = field.widget.attrs.get("class", "")
        if "form-control" not in current and "form-select" not in current:
            if field.widget.__class__.__name__.lower().find("select") >= 0:
                field.widget.attrs["class"] = (current + " form-select").strip()
            elif field.widget.__class__.__name__.lower().find("checkbox") >= 0:
                field.widget.attrs["class"] = (current + " form-check-input").strip()
            else:
                field.widget.attrs["class"] = (current + " form-control").strip()


def manager_login(request):
    if request.user.is_authenticated and _is_manager(request.user):
        return redirect("manager_dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    _style_form(form)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("manager_dashboard")

    return render(request, "parking/manager/login.html", {"form": form})


def manager_logout(request):
    logout(request)
    return redirect("manager_login")


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_dashboard(request):
    active_users = ParkingUser.objects.filter(is_active=True).count()
    total_capacity = sum(p.capacity for p in ParkingLot.objects.all())
    total_available = sum(p.available_slots() for p in ParkingLot.objects.all())

    context = {
        "now": timezone.now(),
        "total_areas": Area.objects.count(),
        "total_parkings": ParkingLot.objects.count(),
        "active_users": active_users,
        "total_prices": ParkingPrice.objects.count(),
        "total_capacity": total_capacity,
        "total_available": total_available,
        "recent_users": ParkingUser.objects.order_by("-created_at")[:6],
        "recent_logs": ActivityLog.objects.order_by("-created_at")[:8],
    }
    return render(request, "parking/manager/dashboard.html", context)


def _build_rows(queryset, columns):
    rows = []
    for obj in queryset:
        row = []
        for col in columns:
            value = getattr(obj, col)
            if callable(value):
                value = value()
            row.append(value)
        rows.append({"obj": obj, "values": row})
    return rows


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_list(request, entity):
    config = MANAGER_MODELS.get(entity)
    if not config:
        return redirect("manager_dashboard")

    model = config["model"]
    q = request.GET.get("q", "").strip()
    queryset = model.objects.all().order_by("-id")

    if q:
        for field in ("name", "full_name", "phone", "license_plate", "district", "action"):
            if any(f.name == field for f in model._meta.get_fields()):
                queryset = queryset.filter(**{f"{field}__icontains": q})
                break

    context = {
        "entity": entity,
        "title": config["title"],
        "columns": config["columns"],
        "rows": _build_rows(queryset, config["columns"]),
        "readonly": config.get("readonly", False),
        "query": q,
    }
    return render(request, "parking/manager/list.html", context)


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_create(request, entity):
    config = MANAGER_MODELS.get(entity)
    if not config or config.get("readonly"):
        return redirect("manager_list", entity=entity)

    model = config["model"]
    FormClass = modelform_factory(model, fields=config["fields"])
    form = FormClass(request.POST or None)
    _style_form(form)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Tao moi thanh cong.")
            return redirect("manager_list", entity=entity)
        except ValidationError as exc:
            form.add_error(None, exc)

    return render(
        request,
        "parking/manager/form.html",
        {
            "entity": entity,
            "title": config["title"],
            "form": form,
            "mode": "create",
        },
    )


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_edit(request, entity, pk):
    config = MANAGER_MODELS.get(entity)
    if not config or config.get("readonly"):
        return redirect("manager_list", entity=entity)

    model = config["model"]
    instance = get_object_or_404(model, pk=pk)
    FormClass = modelform_factory(model, fields=config["fields"])
    form = FormClass(request.POST or None, instance=instance)
    _style_form(form)

    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Cap nhat thanh cong.")
            return redirect("manager_list", entity=entity)
        except ValidationError as exc:
            form.add_error(None, exc)

    return render(
        request,
        "parking/manager/form.html",
        {
            "entity": entity,
            "title": config["title"],
            "form": form,
            "mode": "edit",
            "instance": instance,
        },
    )


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_delete(request, entity, pk):
    config = MANAGER_MODELS.get(entity)
    if not config or config.get("readonly"):
        return redirect("manager_list", entity=entity)

    model = config["model"]
    instance = get_object_or_404(model, pk=pk)

    if request.method == "POST":
        instance.delete()
        messages.success(request, "Da xoa ban ghi.")
        return redirect("manager_list", entity=entity)

    return render(
        request,
        "parking/manager/confirm_delete.html",
        {
            "entity": entity,
            "title": config["title"],
            "instance": instance,
        },
    )
