from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

handler404 = "parking.views.custom_page_not_found"

urlpatterns = [
    path("admin/", RedirectView.as_view(pattern_name="manager_dashboard", permanent=False)),
    path("dj-admin/", admin.site.urls),
    path(settings.MANAGER_URL_PREFIX, include("parking.manager_urls")),
    path("", include("parking.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)