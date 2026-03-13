from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import re
import requests
import unicodedata

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
            "area",
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


def _strip_accents(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _normalize_text(text):
    if not text:
        return ""
    text = _strip_accents(text)
    return text.lower()


def _prepare_address(address):
    if not address:
        return ""
    cleaned = " ".join(address.strip().split())
    cleaned = _strip_accents(cleaned)

    cleaned = re.sub(r"\bTP\.?\s*HCM\b", "Ho Chi Minh City", cleaned, flags=re.I)
    cleaned = re.sub(r"\bTP\.?\s*HN\b", "Ha Noi", cleaned, flags=re.I)
    cleaned = re.sub(r"\bTPHCM\b", "Ho Chi Minh City", cleaned, flags=re.I)
    cleaned = re.sub(r"\bHCM\b", "Ho Chi Minh City", cleaned, flags=re.I)
    cleaned = re.sub(r"\bHN\b", "Ha Noi", cleaned, flags=re.I)
    cleaned = re.sub(r"\bthanh pho ho chi minh\b", "Ho Chi Minh City", cleaned, flags=re.I)
    cleaned = re.sub(r"\bho chi minh\b", "Ho Chi Minh City", cleaned, flags=re.I)
    cleaned = re.sub(r"\bthanh pho ha noi\b", "Ha Noi", cleaned, flags=re.I)
    cleaned = re.sub(r"\bha noi\b", "Ha Noi", cleaned, flags=re.I)
    cleaned = re.sub(r"\bQ\.?\s*(\d+)\b", r"Quan \1", cleaned, flags=re.I)
    cleaned = re.sub(r"\bP\.?\s*(\d+)\b", r"Phuong \1", cleaned, flags=re.I)

    if not re.search(r"\bViet Nam\b|\bVietnam\b", cleaned, flags=re.I):
        cleaned = f"{cleaned}, Viet Nam"

    return cleaned


def _build_query_variants(address):
    if not address:
        return []
    original = " ".join(address.strip().split())
    prepared = _prepare_address(original)
    ascii_original = _strip_accents(original)
    ascii_prepared = _strip_accents(prepared)
    variants = [original, prepared, ascii_original, ascii_prepared]
    extra = []
    for v in variants:
        v_no_country = re.sub(r",?\s*(viet nam|vietnam)\s*$", "", v, flags=re.I).strip(" ,")
        if v_no_country:
            extra.append(v_no_country)
    variants += extra
    seen = []
    for v in variants:
        v = " ".join(v.strip().split())
        if v and v not in seen:
            seen.append(v)
    return seen


def _has_house_number(address):
    return bool(re.search(r"\b\d+[A-Za-z0-9\/-]*\b", address or ""))


def _extract_address_components(address):
    if not address:
        return {}
    ascii_addr = _strip_accents(" ".join(address.strip().split()))
    parts = [p.strip() for p in ascii_addr.split(",") if p.strip()]
    house_number = None
    road = None
    if parts:
        m = re.match(r"^(\d+[A-Za-z0-9\/-]*)\s+(.*)$", parts[0])
        if m:
            house_number = m.group(1)
            road = m.group(2)
        else:
            road = parts[0]
    suburb = None
    district = None
    city = None
    for seg in parts[1:]:
        if re.search(r"\bphuong\b|\bxa\b|\bward\b", seg):
            suburb = seg
        elif re.search(r"\bquan\b|\bhuyen\b|\bdistrict\b", seg):
            district = seg
        elif re.search(r"ho chi minh city|ha noi", seg):
            city = seg
        elif re.search(r"thanh pho", seg):
            city = seg
    if not city:
        for seg in reversed(parts):
            if re.search(r"viet nam|vietnam", seg):
                continue
            city = seg
            break
    return {
        "house_number": house_number,
        "road": road,
        "suburb": suburb,
        "district": district,
        "city": city,
    }


def _result_has_house_number(result):
    addr = result.get("address") if isinstance(result.get("address"), dict) else {}
    return bool(addr.get("house_number") or addr.get("housenumber"))


def _build_structured_queries(address):
    comps = _extract_address_components(address)
    road = comps.get("road")
    if not road:
        return []
    params = []
    base = {"country": "Viet Nam"}
    if comps.get("city"):
        base["city"] = comps["city"]
    if comps.get("district"):
        base["county"] = comps["district"]
    if comps.get("suburb"):
        base["suburb"] = comps["suburb"]
    if comps.get("house_number"):
        p = dict(base)
        p["street"] = f"{comps['house_number']} {road}"
        params.append(p)
    p2 = dict(base)
    p2["street"] = road
    params.append(p2)
    return params


def _normalized_variants(address):
    variants = []
    if address:
        variants.append(_normalize_text(address))
    prepared = _prepare_address(address)
    if prepared:
        variants.append(_normalize_text(prepared))
    trimmed = []
    for v in variants:
        v2 = v.replace("viet nam", "").replace("vietnam", "").strip(" ,")
        if v2:
            trimmed.append(v2)
    return list(dict.fromkeys(variants + trimmed))

def _build_viewbox(address_norm):
    if any(k in address_norm for k in ["ho chi minh", "tphcm", "tp.hcm", "hcm"]):
        return "106.4,10.7,106.95,10.95"
    if "ha noi" in address_norm or "hanoi" in address_norm:
        return "105.7,20.9,106.1,21.1"
    return None

def _score_result(address_norms, result):
    display = _normalize_text(result.get("display_name", ""))
    score = 0

    tokens = set()
    for norm in address_norms:
        for token in norm.split(","):
            token = token.strip()
            if token:
                tokens.add(token)
    for token in tokens:
        if token in display:
            score += 2

    details = result.get("address", {})
    details_text = _normalize_text(" ".join(str(v) for v in details.values()))
    for token in tokens:
        if token in details_text:
            score += 2

    for norm in address_norms:
        first_part = norm.split(",")[0].strip()
        if first_part and first_part in display:
            score += 1

    query_has_number = any(re.search(r"\b\d", norm) for norm in address_norms)
    if query_has_number:
        if _result_has_house_number(result):
            score += 3
        else:
            score -= 2

    try:
        score += float(result.get("importance") or 0) * 1.5
    except (TypeError, ValueError):
        pass

    return score
def _nominatim_headers():
    return {"User-Agent": "webgis-parking/1.0"}


def _nominatim_search(query, address_norms, limit=5):
    viewbox = None
    for norm in address_norms:
        viewbox = _build_viewbox(norm) or viewbox

    params = {
        "format": "jsonv2",
        "q": query,
        "limit": limit,
        "countrycodes": "vn",
        "addressdetails": 1,
        "accept-language": "vi",
    }
    if viewbox:
        params["viewbox"] = viewbox
        params["bounded"] = 1

    res = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params=params,
        headers=_nominatim_headers(),
        timeout=10,
    )
    res.raise_for_status()
    return res.json(), address_norms


def _nominatim_search_structured(params, address_norms, limit=5):
    viewbox = None
    for norm in address_norms:
        viewbox = _build_viewbox(norm) or viewbox

    base = {
        "format": "jsonv2",
        "limit": limit,
        "countrycodes": "vn",
        "addressdetails": 1,
        "accept-language": "vi",
    }
    base.update(params or {})
    if viewbox:
        base["viewbox"] = viewbox
        base["bounded"] = 1

    res = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params=base,
        headers=_nominatim_headers(),
        timeout=10,
    )
    res.raise_for_status()
    return res.json(), address_norms


def _photon_search(query, limit=6):
    res = requests.get(
        "https://photon.komoot.io/api/",
        params={
            "q": query,
            "limit": limit,
            "lang": "vi",
        },
        headers=_nominatim_headers(),
        timeout=10,
    )
    res.raise_for_status()
    data = res.json() or {}
    results = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        name = props.get("name") or props.get("label")
        city = props.get("city") or props.get("state") or props.get("country")
        display = name or props.get("label")
        if city and display:
            display = f"{display}, {city}"
        coords = feat.get("geometry", {}).get("coordinates") or []
        if len(coords) >= 2 and display:
            results.append({
                "display_name": display,
                "lat": coords[1],
                "lon": coords[0],
                "address": props,
            })
    return results


def _search_address(address, limit=6):
    address_norms = _normalized_variants(address)
    queries = _build_query_variants(address)
    data = []

    for query in queries:
        try:
            data, _ = _nominatim_search(query, address_norms, limit=limit)
        except requests.RequestException:
            data = []
        if data:
            break

    if not data:
        structured = _build_structured_queries(address)
        for params in structured:
            try:
                data, _ = _nominatim_search_structured(params, address_norms, limit=limit)
            except requests.RequestException:
                data = []
            if data:
                break

    if not data:
        for query in queries:
            try:
                data = _photon_search(query, limit=limit)
            except requests.RequestException:
                data = []
            if data:
                break

    return data, address_norms

def _rank_results(address_norms, data):
    scored = []
    for row in data:
        scored.append((_score_result(address_norms, row), row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored]

def _geocode_address(address):
    if not address:
        raise ValidationError("Dia chi khong hop le.")

    try:
        data, address_norms = _search_address(address, limit=6)
    except requests.RequestException:
        raise ValidationError("Khong the lay toa do. Kiem tra ket noi Internet.")

    if not data:
        raise ValidationError("Khong tim thay dia chi. Hay kiem tra lai.")

    best = _rank_results(address_norms, data)[0]
    return float(best["lat"]), float(best["lon"])

def _geocode_address_full(address):
    if not address:
        return None
    data, address_norms = _search_address(address, limit=8)
    if not data:
        return None
    best = _rank_results(address_norms, data)[0]
    query_has_number = _has_house_number(address)
    approximate = query_has_number and not _result_has_house_number(best)
    return {
        "display_name": best.get("display_name"),
        "lat": best.get("lat"),
        "lon": best.get("lon"),
        "approximate": approximate,
    }
class ParkingLotManagerForm(forms.ModelForm):
    address_input = forms.CharField(required=False, label="Dia chi")
    geo_lat = forms.FloatField(required=False, widget=forms.HiddenInput())
    geo_lon = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = ParkingLot
        fields = ["name", "area", "district", "capacity", "is_active", "revenue"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            "name",
            "address_input",
            "area",
            "district",
            "capacity",
            "is_active",
            "revenue",
            "geo_lat",
            "geo_lon",
        ])
        if self.instance and self.instance.pk and self.instance.address:
            self.fields["address_input"].initial = self.instance.address
        if self.instance and self.instance.pk:
            if self.instance.latitude is not None:
                self.fields["geo_lat"].initial = self.instance.latitude
            if self.instance.longitude is not None:
                self.fields["geo_lon"].initial = self.instance.longitude

    def clean(self):
        cleaned = super().clean()
        address_input = (cleaned.get("address_input") or "").strip()
        geo_lat = cleaned.get("geo_lat")
        geo_lon = cleaned.get("geo_lon")

        if not address_input:
            raise ValidationError("Hay nhap dia chi.")

        cleaned["_address_input"] = address_input
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        address_input = self.cleaned_data.get("_address_input", "")
        geo_lat = self.cleaned_data.get("geo_lat")
        geo_lon = self.cleaned_data.get("geo_lon")

        if address_input:
            address_changed = False
            if instance.pk:
                address_changed = address_input.strip() != (instance.address or "").strip()

            if geo_lat is not None and geo_lon is not None:
                if address_changed and instance.latitude is not None and instance.longitude is not None:
                    if abs(geo_lat - instance.latitude) < 0.000001 and abs(geo_lon - instance.longitude) < 0.000001:
                        lat, lon = _geocode_address(address_input)
                    else:
                        lat, lon = geo_lat, geo_lon
                else:
                    lat, lon = geo_lat, geo_lon
            else:
                lat, lon = _geocode_address(address_input)

            instance.latitude = lat
            instance.longitude = lon

        if address_input:
            instance.address = address_input
        if commit:
            instance.save()
        return instance


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
    if entity == "parkings":
        FormClass = ParkingLotManagerForm
    else:
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

    if entity == "parkings":
        FormClass = ParkingLotManagerForm
    else:
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


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_geocode_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 3:
        return JsonResponse({"results": []})

    try:
        data, address_norms = _search_address(q, limit=8)
    except requests.RequestException:
        return JsonResponse({"results": []})

    ranked = _rank_results(address_norms, data)[:6]
    results = [
        {
            "display_name": r.get("display_name"),
            "lat": r.get("lat"),
            "lon": r.get("lon"),
        }
        for r in ranked
    ]
    return JsonResponse({"results": results})

@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_geocode_forward(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 3:
        return JsonResponse({"ok": False, "error": "Nhap dia chi day du."})

    try:
        best = _geocode_address_full(q)
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "Khong the ket noi dich vu dinh vi."})

    if not best:
        return JsonResponse({"ok": False, "error": "Khong tim thay dia chi."})

    return JsonResponse({
        "ok": True,
        "display_name": best.get("display_name"),
        "lat": best.get("lat"),
        "lon": best.get("lon"),
        "approximate": bool(best.get("approximate")),
    })


@login_required(login_url="manager_login")
@user_passes_test(_is_manager, login_url="manager_login")
def manager_geocode_reverse(request):
    try:
        lat = float(request.GET.get("lat"))
        lon = float(request.GET.get("lon"))
    except (TypeError, ValueError):
        return JsonResponse({"display_name": ""})

    try:
        res = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lon,
                "zoom": 18,
                "addressdetails": 1,
                "accept-language": "vi",
            },
            headers=_nominatim_headers(),
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
    except requests.RequestException:
        return JsonResponse({"display_name": ""})

    return JsonResponse({"display_name": data.get("display_name", "")})
























