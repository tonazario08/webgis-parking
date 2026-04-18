from django.contrib import admin

from .models import Area, ParkingLot, ParkingLotImage, ParkingPrice, ParkingRegistrationRequest, ParkingUser


class ParkingLotImageInline(admin.TabularInline):
    model = ParkingLotImage
    extra = 0


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "capacity", "is_active", "revenue")
    search_fields = ("name", "address", "district", "short_description")
    inlines = [ParkingLotImageInline]


admin.site.register(Area)
admin.site.register(ParkingUser)
admin.site.register(ParkingPrice)
admin.site.register(ParkingRegistrationRequest)
