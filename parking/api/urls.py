"""
URL Configuration cho GIS APIs
"""

from django.urls import path
from . import gis_views

app_name = 'parking'

urlpatterns = [
    # GIS APIs
    path('api/gis/nearby-parkings/', gis_views.nearby_parkings, name='nearby_parkings'),
    path('api/gis/nearest-parking/', gis_views.nearest_parking, name='nearest_parking'),
    path('api/gis/route/', gis_views.calculate_route, name='calculate_route'),
    path('api/gis/route-to-parking/', gis_views.route_to_parking, name='route_to_parking'),
    path('api/gis/export-geojson/', gis_views.export_geojson, name='export_geojson'),
    path('api/gis/health/', gis_views.gis_health, name='gis_health'),
]