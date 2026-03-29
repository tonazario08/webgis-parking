from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('map/', views.map_view, name='map_view'),
    path('list/', views.parking_list, name='parking_list'),
    path('available/', views.parking_available, name='parking_available'),
    path('revenue/', views.revenue_view, name='revenue_view'),
    path('areas/', views.areas_view, name='areas_view'),
    path('activity/', views.activity_log_view, name='activity_log_view'),

    path('search/', views.search_by_phone, name='search_by_phone'),
    path('customer/<int:id>/', views.parking_user_detail, name='parking_user_detail'),
    path('customer/<int:user_id>/', views.parking_user_detail, name='customer_detail'),
    path('verify-email/<int:user_id>/<str:token>/', views.verify_parking_user_email, name='parking_user_verify_email'),
    path('checkout/<int:user_id>/', views.checkout_vehicle, name='checkout_vehicle'),
    path('parking/<int:id>/', views.parking_detail, name='parking_detail'),

    path('api/parkings/', views.parking_map_data, name='parking_map_data'),
    path('api/nearest-parking/', views.api_find_nearest_parking, name='api_find_nearest_parking'),
    path('api/route/', views.api_route, name='api_route'),
]
