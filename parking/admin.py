from django.contrib import admin
from .models import Area, ParkingLot, ParkingUser, ActivityLog, ParkingStatus


# ===============================
# KHU VỰC
# ===============================
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


# ===============================
# TRẠNG THÁI BÃI ĐỖ
# ===============================
@admin.register(ParkingStatus)
class ParkingStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_code')
    search_fields = ('name',)


# ===============================
# BÃI ĐỖ XE
# ===============================
@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'area',
        'capacity',
        'available_slots',
        'is_active',
        'latitude',
        'longitude'
    )

    list_filter = ('is_active', 'area')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at',)

    fieldsets = (
        ("Thông tin chung", {
            "fields": ('name', 'address', 'area', 'status')
        }),
        ("Vị trí GIS", {
            "fields": ('latitude', 'longitude')
        }),
        ("Sức chứa & giá", {
            "fields": ('capacity', 'available_slots', 'price_per_hour')
        }),
        ("Tiện ích", {
            "fields": ('has_security', 'has_camera', 'has_ev_charging')
        }),
        ("Trạng thái", {
            "fields": ('is_active', 'is_24h')
        }),
    )


# ===============================
# XE ĐANG ĐỖ
# ===============================
@admin.register(ParkingUser)
class ParkingUserAdmin(admin.ModelAdmin):
    list_display = (
        'license_plate',
        'parking_lot',
        'checkin_time',
        'checkout_time',
        'is_active'
    )

    list_filter = ('is_active', 'parking_lot')
    search_fields = ('license_plate',)
    readonly_fields = ('checkin_time',)


# ===============================
# NHẬT KÝ HOẠT ĐỘNG
# ===============================
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'parking_lot', 'time')
    list_filter = ('parking_lot',)
    search_fields = ('action',)
    readonly_fields = ('time',)
