from django.urls import path
from . import manager_views

urlpatterns = [
    path("login/", manager_views.manager_login, name="manager_login"),
    path("logout/", manager_views.manager_logout, name="manager_logout"),
    path("", manager_views.manager_dashboard, name="manager_dashboard"),
    path("registrations/", manager_views.manager_registration_list, name="manager_registrations"),
    path(
        "registrations/<int:pk>/approve/",
        manager_views.manager_registration_approve,
        name="manager_registration_approve",
    ),
    path(
        "registrations/<int:pk>/reject/",
        manager_views.manager_registration_reject,
        name="manager_registration_reject",
    ),
    path("geocode/suggest/", manager_views.manager_geocode_suggest, name="manager_geocode_suggest"),
    path("geocode/forward/", manager_views.manager_geocode_forward, name="manager_geocode_forward"),
    path("geocode/reverse/", manager_views.manager_geocode_reverse, name="manager_geocode_reverse"),
    path("excel/", manager_views.manager_excel_page, name="manager_excel"),
    path("excel/template/<str:entity>/", manager_views.manager_excel_template, name="manager_excel_template"),
    path("excel/import/<str:entity>/", manager_views.manager_excel_import, name="manager_excel_import"),
    path("excel/export/<str:entity>/", manager_views.manager_excel_export, name="manager_excel_export"),
    path("roles/", manager_views.manager_roles, name="manager_roles"),
    path("roles/<int:user_id>/assign/", manager_views.manager_assign_role, name="manager_assign_role"),
    path("<str:entity>/", manager_views.manager_list, name="manager_list"),
    path("trash/<str:entity>/", manager_views.manager_trash_list, name="manager_trash"),
    path("trash/<str:entity>/<int:pk>/restore/", manager_views.manager_restore, name="manager_restore"),
    path("<str:entity>/create/", manager_views.manager_create, name="manager_create"),
    path("<str:entity>/<int:pk>/edit/", manager_views.manager_edit, name="manager_edit"),
    path("<str:entity>/<int:pk>/delete/", manager_views.manager_delete, name="manager_delete"),
    
]
