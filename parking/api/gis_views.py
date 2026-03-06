# parking/api/gis_views.py

"""
GIS API Views cho Hệ thống Quản lý Bãi đỗ xe Đô thị
===================================================

Views chỉ xử lý request/response.
Logic GIS nằm trong parking.utils.gis
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from parking.models import ParkingLot, ParkingStatus
import json


# =============================================================================
# LAZY GIS IMPORT
# =============================================================================

def _get_gis():
    from parking.utils import gis
    return gis


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def success_response(data, message="Success", status=200):
    return JsonResponse(
        {"status": "success", "message": message, "data": data},
        status=status
    )


def error_response(message, errors=None, status=400):
    payload = {"status": "error", "message": message}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def validate_required_params(data, required):
    missing = [p for p in required if p not in data]
    return len(missing) == 0, missing


# =============================================================================
# API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def nearby_parkings(request):
    try:
        data = request.GET if request.method == "GET" else json.loads(request.body)

        ok, missing = validate_required_params(data, ["latitude", "longitude", "radius"])
        if not ok:
            return error_response("Missing required parameters", missing)

        lat = float(data["latitude"])
        lon = float(data["longitude"])
        radius = float(data["radius"])

        gis = _get_gis()
        if not gis.validate_coordinates(lat, lon):
            return error_response("Invalid coordinates")

        parkings = gis.find_nearby_parkings(
            ParkingLot.objects.filter(is_active=True),
            lat, lon, radius
        )

        return success_response({
            "center": {"latitude": lat, "longitude": lon},
            "radius_km": radius,
            "total_found": len(parkings),
            "parkings": parkings
        })

    except Exception as e:
        return error_response(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def nearest_parking(request):
    try:
        data = request.GET if request.method == "GET" else json.loads(request.body)

        ok, missing = validate_required_params(data, ["latitude", "longitude"])
        if not ok:
            return error_response("Missing required parameters", missing)

        lat = float(data["latitude"])
        lon = float(data["longitude"])
        max_radius = float(data.get("max_radius", 50))

        gis = _get_gis()
        nearest = gis.find_nearest_parking(
            ParkingLot.objects.filter(is_active=True),
            lat, lon, max_radius
        )

        return success_response({"nearest_parking": nearest})

    except Exception as e:
        return error_response(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calculate_route(request):
    try:
        data = request.GET if request.method == "GET" else json.loads(request.body)

        ok, missing = validate_required_params(
            data, ["start_lat", "start_lon", "end_lat", "end_lon"]
        )
        if not ok:
            return error_response("Missing required parameters", missing)

        slat = float(data["start_lat"])
        slon = float(data["start_lon"])
        elat = float(data["end_lat"])
        elon = float(data["end_lon"])

        gis = _get_gis()
        route = gis.calculate_route_simple(slat, slon, elat, elon)

        return success_response({
            "start": {"lat": slat, "lon": slon},
            "end": {"lat": elat, "lon": elon},
            "route": route
        })

    except Exception as e:
        return error_response(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def route_to_parking(request):
    try:
        data = request.GET if request.method == "GET" else json.loads(request.body)

        ok, missing = validate_required_params(
            data, ["start_lat", "start_lon", "parking_id"]
        )
        if not ok:
            return error_response("Missing required parameters", missing)

        slat = float(data["start_lat"])
        slon = float(data["start_lon"])
        parking_id = int(data["parking_id"])

        parking = ParkingLot.objects.get(id=parking_id, is_active=True)

        gis = _get_gis()
        route = gis.calculate_route_simple(
            slat, slon, parking.latitude, parking.longitude
        )

        return success_response({
            "parking": {
                "id": parking.id,
                "name": parking.name,
                "latitude": parking.latitude,
                "longitude": parking.longitude,
                "status": parking.status.name if parking.status else None
            },
            "route": route
        })

    except ParkingLot.DoesNotExist:
        return error_response("Parking not found", status=404)
    except Exception as e:
        return error_response(str(e), status=500)


@require_GET
def filter_by_status(request):
    status_name = request.GET.get("status")
    if not status_name:
        return error_response("Missing status parameter")

    try:
        status = ParkingStatus.objects.get(name__iexact=status_name)
    except ParkingStatus.DoesNotExist:
        return error_response("Status not found", status=404)

    parkings = ParkingLot.objects.filter(status=status, is_active=True)

    data = [
        {
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
            "available_slots": p.available_slots,
            "capacity": p.capacity,
            "status": status.name
        }
        for p in parkings
    ]

    return success_response(data)


@require_GET
def export_geojson(request):
    try:
        gis = _get_gis()
        geojson = gis.export_parkings_geojson(ParkingLot.objects.filter(is_active=True))
        return JsonResponse(geojson, safe=False)
    except Exception as e:
        return error_response(str(e), status=500)


@require_GET
def gis_health(request):
    try:
        return success_response({
            "total_parkings": ParkingLot.objects.count(),
            "active_parkings": ParkingLot.objects.filter(is_active=True).count()
        })
    except Exception as e:
        return error_response(str(e), status=500)
