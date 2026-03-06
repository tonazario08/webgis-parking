from django.db import models
from django.utils import timezone


class Area(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class ParkingStatus(models.Model):
    name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=10, default="#999999")

    def __str__(self):
        return self.name


class ParkingLot(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)

    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, related_name="parkings"
    )
    status = models.ForeignKey(
        ParkingStatus, on_delete=models.SET_NULL, null=True, blank=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)

    capacity = models.IntegerField(default=0)
    available_slots = models.IntegerField(default=0)
    price_per_hour = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_24h = models.BooleanField(default=False)

    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    has_security = models.BooleanField(default=False)
    has_camera = models.BooleanField(default=False)
    has_ev_charging = models.BooleanField(default=False)

    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ================== METHODS FOR GIS ==================

    def get_capacity_percent(self):
        if self.capacity <= 0:
            return 0
        return int((self.available_slots / self.capacity) * 100)

    def is_full(self):
        return self.available_slots <= 0

    def is_nearly_full(self):
        if self.capacity <= 0:
            return False
        return self.available_slots / self.capacity <= 0.1

    def get_status(self):
        return self.status

    def __str__(self):
        return self.name


class ParkingUser(models.Model):
    parking_lot = models.ForeignKey(
        ParkingLot, on_delete=models.CASCADE, related_name="parking_users"
    )
    license_plate = models.CharField(max_length=20)
    checkin_time = models.DateTimeField(default=timezone.now)
    checkout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.license_plate


class ActivityLog(models.Model):
    action = models.CharField(max_length=255)
    parking_lot = models.ForeignKey(
        ParkingLot, on_delete=models.SET_NULL, null=True, blank=True
    )
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.action
