from django.contrib import admin
from .models import Area, ParkingLot, ParkingUser

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'used_slots', 'available_slots', 'is_active')


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
