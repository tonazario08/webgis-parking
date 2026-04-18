from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", RedirectView.as_view(pattern_name="manager_dashboard", permanent=False)),
    path("dj-admin/", admin.site.urls),
    path("manager/", include("parking.manager_urls")),
    path("", include("parking.urls")),
]

handler404 = "parking.views.custom_page_not_found"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
