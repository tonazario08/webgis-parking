from django.urls import path
from . import manager_views

urlpatterns = [
    path("login/", manager_views.manager_login, name="manager_login"),
    path("logout/", manager_views.manager_logout, name="manager_logout"),
    path("", manager_views.manager_dashboard, name="manager_dashboard"),
    path("<str:entity>/", manager_views.manager_list, name="manager_list"),
    path("<str:entity>/create/", manager_views.manager_create, name="manager_create"),
    path("<str:entity>/<int:pk>/edit/", manager_views.manager_edit, name="manager_edit"),
    path("<str:entity>/<int:pk>/delete/", manager_views.manager_delete, name="manager_delete"),
]
