"""
GIS API Views cho Hệ thống Quản lý Bãi đỗ xe Đô thị
===================================================

Module này chứa các API endpoints để xử lý yêu cầu GIS từ frontend/client.
Views này CHỈ xử lý request/response, logic GIS nằm trong utils/gis.py

Author: GIS Backend Team
Date: 2026-02-04
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from parking.models import ParkingLot as Parking
import json
# Note: import `parking.utils.gis` lazily inside views to avoid import-time errors on startup (sanitization required in utils)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def success_response(data, message="Success", status=200):
    """Tạo JSON response thành công."""
    return JsonResponse({
        'status': 'success',
        'message': message,
        'data': data
    }, status=status)


def error_response(message, errors=None, status=400):
    """Tạo JSON response lỗi."""
    response_data = {'status': 'error', 'message': message}
    if errors:
        response_data['errors'] = errors
    return JsonResponse(response_data, status=status)


def validate_required_params(request_data, required_params):
    """Kiểm tra các tham số bắt buộc."""
    missing = [p for p in required_params if p not in request_data]
    return len(missing) == 0, missing


# =============================================================================
# API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def nearby_parkings(request):
    """
    API: Tìm bãi đỗ xe trong bán kính.
    
    Endpoint: /api/gis/nearby-parkings/
    
    Parameters:
        - latitude, longitude, radius (required)
        - only_active, only_available, min_slots, sort_by_distance (optional)
    """
    try:
        from parking.utils import gis
        data = request.GET if request.method == 'GET' else json.loads(request.body)
        
        # Validate
        is_valid, missing = validate_required_params(data, ['latitude', 'longitude', 'radius'])
        if not is_valid:
            return error_response('Missing required parameters', errors=missing)
        
        # Parse
        center_lat = float(data.get('latitude'))
        center_lon = float(data.get('longitude'))
        radius_km = float(data.get('radius'))
        
        if not gis.validate_coordinates(center_lat, center_lon):
            return error_response('Invalid coordinates')
        
        if radius_km <= 0 or radius_km > 100:
            return error_response('Radius must be between 0 and 100 km')
        
        # Optional params
        only_active = data.get('only_active', 'true').lower() in ['true', '1', 'yes']
        only_available = data.get('only_available', 'false').lower() in ['true', '1', 'yes']
        min_slots = int(data.get('min_slots', 0))
        sort_by_distance = data.get('sort_by_distance', 'true').lower() in ['true', '1', 'yes']
        
        # Find parkings
        parkings = gis.find_nearby_parkings(
            Parking.objects.all(), center_lat, center_lon, radius_km,
            only_active=only_active, only_available=only_available,
            min_slots=min_slots, sort_by_distance=sort_by_distance
        )
        
        return success_response({
            'center': {'latitude': center_lat, 'longitude': center_lon},
            'radius_km': radius_km,
            'total_found': len(parkings),
            'parkings': parkings
        }, message=f'Found {len(parkings)} parking(s) within {radius_km}km')
        
    except (ValueError, TypeError):
        return error_response('Invalid parameter types')
    except json.JSONDecodeError:
        return error_response('Invalid JSON format')
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def nearest_parking(request):
    """
    API: Tìm bãi đỗ xe GẦN NHẤT.
    
    Endpoint: /api/gis/nearest-parking/
    
    Parameters:
        - latitude, longitude (required)
        - max_radius, only_active, only_available (optional)
    """
    try:
        from parking.utils import gis
        data = request.GET if request.method == 'GET' else json.loads(request.body)
        
        is_valid, missing = validate_required_params(data, ['latitude', 'longitude'])
        if not is_valid:
            return error_response('Missing required parameters', errors=missing)
        
        center_lat = float(data.get('latitude'))
        center_lon = float(data.get('longitude'))
        max_radius_km = float(data.get('max_radius', 50.0))
        
        if not gis.validate_coordinates(center_lat, center_lon):
            return error_response('Invalid coordinates')
        
        only_active = data.get('only_active', 'true').lower() in ['true', '1', 'yes']
        only_available = data.get('only_available', 'false').lower() in ['true', '1', 'yes']
        
        nearest = gis.find_nearest_parking(
            Parking.objects.all(), center_lat, center_lon, max_radius_km,
            only_active=only_active, only_available=only_available
        )
        
        message = f"Found nearest parking: {nearest['name']}" if nearest else f"No parking found within {max_radius_km}km"
        
        return success_response({
            'center': {'latitude': center_lat, 'longitude': center_lon},
            'max_radius_km': max_radius_km,
            'nearest_parking': nearest
        }, message=message)
        
    except (ValueError, TypeError):
        return error_response('Invalid parameter types')
    except json.JSONDecodeError:
        return error_response('Invalid JSON format')
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def calculate_route(request):
    """
    API: Tính route tối ưu giữa 2 điểm.
    
    Endpoint: /api/gis/route/
    
    Parameters:
        - start_lat, start_lon, end_lat, end_lon (required)
        - profile, use_osrm (optional)
    """
    try:
        from parking.utils import gis
        data = request.GET if request.method == 'GET' else json.loads(request.body)
        
        is_valid, missing = validate_required_params(data, ['start_lat', 'start_lon', 'end_lat', 'end_lon'])
        if not is_valid:
            return error_response('Missing required parameters', errors=missing)
        
        start_lat = float(data.get('start_lat'))
        start_lon = float(data.get('start_lon'))
        end_lat = float(data.get('end_lat'))
        end_lon = float(data.get('end_lon'))
        
        if not (gis.validate_coordinates(start_lat, start_lon) and gis.validate_coordinates(end_lat, end_lon)):
            return error_response('Invalid coordinates')
        
        profile = data.get('profile', 'driving')
        if profile not in ['driving', 'cycling', 'walking']:
            profile = 'driving'
        
        use_osrm = data.get('use_osrm', 'true').lower() in ['true', '1', 'yes']
        
        if use_osrm:
            route = gis.calculate_route_osrm(start_lat, start_lon, end_lat, end_lon, profile)
            if route is None:
                route = gis.calculate_route_simple(start_lat, start_lon, end_lat, end_lon)
                message = 'Route simulated (OSRM API unavailable)'
            else:
                message = 'Route calculated successfully'
        else:
            route = gis.calculate_route_simple(start_lat, start_lon, end_lat, end_lon)
            message = 'Route simulated (not actual route)'
        
        bearing = gis.get_bearing(start_lat, start_lon, end_lat, end_lon)
        direction = gis.get_direction_name(bearing)
        
        return success_response({
            'start': {'latitude': start_lat, 'longitude': start_lon},
            'end': {'latitude': end_lat, 'longitude': end_lon},
            'bearing': round(bearing, 2),
            'direction': direction,
            'route': route
        }, message=message)
        
    except (ValueError, TypeError):
        return error_response('Invalid parameter types')
    except json.JSONDecodeError:
        return error_response('Invalid JSON format')
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def route_to_parking(request):
    """
    API: Tính route từ vị trí hiện tại đến bãi đỗ xe cụ thể.
    
    Endpoint: /api/gis/route-to-parking/
    
    Parameters:
        - start_lat, start_lon, parking_id (required)
        - profile, use_osrm (optional)
    """
    try:
        from parking.utils import gis
        data = request.GET if request.method == 'GET' else json.loads(request.body)
        
        is_valid, missing = validate_required_params(data, ['start_lat', 'start_lon', 'parking_id'])
        if not is_valid:
            return error_response('Missing required parameters', errors=missing)
        
        start_lat = float(data.get('start_lat'))
        start_lon = float(data.get('start_lon'))
        parking_id = int(data.get('parking_id'))
        
        if not gis.validate_coordinates(start_lat, start_lon):
            return error_response('Invalid start coordinates')
        
        try:
            parking = Parking.objects.select_related('parking_type', 'khu_vuc').get(id=parking_id)
        except Parking.DoesNotExist:
            return error_response(f'Parking with ID {parking_id} not found', status=404)
        
        profile = data.get('profile', 'driving')
        use_osrm = data.get('use_osrm', 'true').lower() in ['true', '1', 'yes']
        
        end_lat = float(parking.latitude)
        end_lon = float(parking.longitude)
        
        if use_osrm:
            route = gis.calculate_route_osrm(start_lat, start_lon, end_lat, end_lon, profile)
            if route is None:
                route = gis.calculate_route_simple(start_lat, start_lon, end_lat, end_lon)
                message = 'Route simulated (OSRM unavailable)'
            else:
                message = f'Route to {parking.name} calculated'
        else:
            route = gis.calculate_route_simple(start_lat, start_lon, end_lat, end_lon)
            message = f'Route to {parking.name} simulated'
        
        status = parking.get_status()
        parking_info = {
            'id': parking.id,
            'name': parking.name,
            'latitude': end_lat,
            'longitude': end_lon,
            'address': parking.address or '',
            'available_slots': parking.available_slots,
            'total_slots': parking.total_slots,
            'capacity_percent': parking.get_capacity_percent(),
            'parking_type': parking.parking_type.name,
            'khu_vuc': parking.khu_vuc.name,
            'status': {
                'name': status.name if status else 'Unknown',
                'color': status.color_code if status else '#999'
            } if status else None
        }
        
        return success_response({
            'start': {'latitude': start_lat, 'longitude': start_lon},
            'parking': parking_info,
            'route': route
        }, message=message)
        
    except (ValueError, TypeError):
        return error_response('Invalid parameter types')
    except json.JSONDecodeError:
        return error_response('Invalid JSON format')
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["GET"])
def export_geojson(request):
    """
    API: Export dữ liệu bãi đỗ xe sang GeoJSON.
    
    Endpoint: /api/gis/export-geojson/
    
    Query Parameters (optional):
        - khu_vuc_id, parking_type_id
        - only_active, only_available
    """
    try:
        from parking.utils import gis
        queryset = Parking.objects.all()
        
        khu_vuc_id = request.GET.get('khu_vuc_id')
        if khu_vuc_id:
            queryset = queryset.filter(khu_vuc_id=khu_vuc_id)
        
        parking_type_id = request.GET.get('parking_type_id')
        if parking_type_id:
            queryset = queryset.filter(parking_type_id=parking_type_id)
        
        only_active = request.GET.get('only_active', 'true').lower() in ['true', '1', 'yes']
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        only_available = request.GET.get('only_available', 'false').lower() in ['true', '1', 'yes']
        if only_available:
            queryset = queryset.filter(available_slots__gt=0)
        
        geojson = gis.export_parkings_geojson(queryset)
        return JsonResponse(geojson, safe=False)
        
    except Exception as e:
        return error_response(f'Internal server error: {str(e)}', status=500)


@require_http_methods(["GET"])
def gis_health(request):
    """
    API: Kiểm tra trạng thái GIS service.
    
    Endpoint: /api/gis/health/
    """
    try:
        from parking.utils import gis
        total_parkings = Parking.objects.count()
        active_parkings = Parking.objects.filter(is_active=True).count()
        
        osrm_available = False
        try:
            test_route = gis.calculate_route_osrm(10.762622, 106.660172, 10.763, 106.661)
            osrm_available = test_route is not None
        except:
            pass
        
        return success_response({
            'total_parkings': total_parkings,
            'active_parkings': active_parkings,
            'osrm_available': osrm_available,
            'features': ['haversine_distance', 'nearby_search', 'route_calculation', 'geojson_export']
        }, message='GIS service is healthy')
        
    except Exception as e:
        return error_response(f'Service unhealthy: {str(e)}', status=500)