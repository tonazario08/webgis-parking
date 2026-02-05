"""
URL Configuration cho GIS APIs
"""

from django.urls import path
from . import gis_views

app_name = 'parking_api'

urlpatterns = [
    # GIS APIs (mounted at /api/gis/)
    path('nearby-parkings/', gis_views.nearby_parkings, name='nearby_parkings'),
    path('nearest-parking/', gis_views.nearest_parking, name='nearest_parking'),
    path('route/', gis_views.calculate_route, name='calculate_route'),
    path('route-to-parking/', gis_views.route_to_parking, name='route_to_parking'),
    path('export-geojson/', gis_views.export_geojson, name='export_geojson'),
    path('health/', gis_views.gis_health, name='gis_health'),
]