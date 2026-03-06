"""GIS helper functions for parking features."""

import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance between two lat/lon points in kilometers."""
    r = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _get_parking_coordinates(parking):
    """Get parking coordinates with fallback to area coordinates."""
    lat = getattr(parking, "latitude", None)
    lon = getattr(parking, "longitude", None)

    if lat is not None and lon is not None:
        return lat, lon

    area = getattr(parking, "area", None)
    if area is not None:
        area_lat = getattr(area, "latitude", None)
        area_lon = getattr(area, "longitude", None)
        if area_lat is not None and area_lon is not None:
            return area_lat, area_lon

    return None, None


def find_nearest_parking(parking_queryset, user_lat, user_lon, only_available=False):
    """Return nearest parking as a JSON-serializable dict or None."""
    best = None

    for parking in parking_queryset:
        if only_available and hasattr(parking, "available_slots"):
            try:
                if parking.available_slots() <= 0:
                    continue
            except Exception:
                continue

        p_lat, p_lon = _get_parking_coordinates(parking)
        if p_lat is None or p_lon is None:
            continue

        distance_km = haversine_distance(user_lat, user_lon, p_lat, p_lon)

        if best is None or distance_km < best["distance_km"]:
            available = None
            if hasattr(parking, "available_slots"):
                try:
                    available = parking.available_slots()
                except Exception:
                    available = None

            best = {
                "id": parking.id,
                "name": parking.name,
                "distance_km": round(distance_km, 2),
                "lat": float(p_lat),
                "lon": float(p_lon),
                "available_slots": available,
            }

    return best
