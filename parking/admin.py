from django.contrib import admin
from .models import Area, ParkingLot, ParkingUser, ParkingPrice


# ===============================
# KHU VỰC
# ===============================
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)


# ===============================
# INLINE: BẢNG GIÁ GỬI XE
# ===============================
class ParkingPriceInline(admin.TabularInline):
    model = ParkingPrice
    extra = 1


# ===============================
# BÃI ĐỖ XE
# ===============================
@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'capacity',
        'used_slots',
        'available_slots',
        'is_active'
    )

    list_filter = ('is_active',)
    search_fields = ('name',)

    # ❌ LOẠI BỎ GIÁ/GIỜ Ở FORM BÃI ĐỖ XE
    exclude = ('price_per_hour',)

    # ✅ GIỮ BẢNG GIÁ THEO LOẠI XE Ở DƯỚI
    inlines = [ParkingPriceInline]


# ===============================
# NGƯỜI GỬI XE
# ===============================
@admin.register(ParkingUser)
class ParkingUserAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'phone',
        'license_plate',
        'vehicle_type',
        'parking_lot',
        'created_at'
    )
    list_filter = ('vehicle_type', 'parking_lot')
    search_fields = ('full_name', 'phone', 'license_plate')


# ===============================
# BẢNG GIÁ GỬI XE (QUẢN LÝ RIÊNG)
# ===============================
@admin.register(ParkingPrice)
class ParkingPriceAdmin(admin.ModelAdmin):
    list_display = ('parking_lot', 'vehicle_type', 'price_per_hour')
    list_filter = ('vehicle_type',)
