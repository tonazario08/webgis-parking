from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('search/', views.search_by_phone, name='search_by_phone'),
    path('customer/<int:id>/', views.parking_user_detail, name='parking_user_detail'),
    path('customer/<int:user_id>/', views.parking_user_detail, name='customer_detail'),
    path('checkout/<int:user_id>/', views.checkout_vehicle, name='checkout_vehicle'),
    path('parking/<int:id>/', views.parking_detail, name='parking_detail'),
    path('map/', views.map_view, name='map_view'),
]
