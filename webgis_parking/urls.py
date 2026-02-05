from django.contrib import admin
from django.urls import path
from parking.views import home, map_view, parking_list, available_parking, revenue_view, areas_view, parking_detail, activity_log_view
from parking.views import (
    home,
    map_view,
    parking_list,
    available_parking,   # ✅ ĐÚNG TÊN
    revenue_view,
    areas_view,
    parking_detail,
    activity_log_view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('map/', map_view, name='map_view'),
    path('list/', parking_list, name='parking_list'),
    path('available/', available_parking, name='parking_available'),
    path('revenue/', revenue_view, name='revenue_view'),
    path('areas/', areas_view, name='areas_view'),
    path('parking/<int:id>/', parking_detail, name='parking_detail'),
    path('activity/', activity_log_view, name='activity_log_view'),
]
