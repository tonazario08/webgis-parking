from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import PublicPasswordResetForm, PublicSetPasswordForm

urlpatterns = [
    path("", views.home, name="home"),
    path("dang-ky-gui-xe/", views.parking_registration_create, name="parking_registration_create"),
    path("lich-su-dang-ky/", views.parking_registration_history, name="parking_registration_history"),
    path("login/", views.public_login, name="login"),
    path("register/", views.public_register, name="register"),
    path("register/verify-otp/", views.verify_otp, name="verify_otp"),
    path("logout/", views.public_logout, name="logout"),
    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            form_class=PublicPasswordResetForm,
            template_name="parking/auth/password_reset_form.html",
            email_template_name="parking/auth/password_reset_email.txt",
            subject_template_name="parking/auth/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="parking/auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=PublicSetPasswordForm,
            template_name="parking/auth/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="parking/auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("map/", views.map_view, name="map_view"),
    path("list/", views.parking_list, name="parking_list"),
    path("available/", views.parking_available, name="parking_available"),
    path("areas/", views.areas_view, name="areas_view"),
    path("activity/", views.activity_log_view, name="activity_log_view"),
    path("search/", views.search_by_phone, name="search_by_phone"),
    path("customer/<int:id>/", views.parking_user_detail, name="parking_user_detail"),
    path("customer/<int:user_id>/", views.parking_user_detail, name="customer_detail"),
    path(
        "verify-email/<int:user_id>/<str:token>/",
        views.verify_parking_user_email,
        name="parking_user_verify_email",
    ),
    path("checkout/<int:user_id>/", views.checkout_vehicle, name="checkout_vehicle"),
    path("parking/<int:id>/", views.parking_detail, name="parking_detail"),
    path("api/parkings/", views.parking_map_data, name="parking_map_data"),
    path("api/nearest-parking/", views.api_find_nearest_parking, name="api_find_nearest_parking"),
    path("api/route/", views.api_route, name="api_route"),
]
