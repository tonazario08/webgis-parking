from django.urls import path
from . import manager_views

urlpatterns = [
    path("login/", manager_views.manager_login, name="manager_login"),
    path("logout/", manager_views.manager_logout, name="manager_logout"),
    path("", manager_views.manager_dashboard, name="manager_dashboard"),
    path("geocode/suggest/", manager_views.manager_geocode_suggest, name="manager_geocode_suggest"),
    path("geocode/forward/", manager_views.manager_geocode_forward, name="manager_geocode_forward"),
    path("geocode/reverse/", manager_views.manager_geocode_reverse, name="manager_geocode_reverse"),
    path("<str:entity>/", manager_views.manager_list, name="manager_list"),
    path("<str:entity>/create/", manager_views.manager_create, name="manager_create"),
    path("<str:entity>/<int:pk>/edit/", manager_views.manager_edit, name="manager_edit"),
    path("<str:entity>/<int:pk>/delete/", manager_views.manager_delete, name="manager_delete"),
]
