from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', RedirectView.as_view(pattern_name='manager_dashboard', permanent=False)),
    path('dj-admin/', admin.site.urls),
    path('manager/', include('parking.manager_urls')),
    path('', include('parking.urls')),
]
