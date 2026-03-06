from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Area(models.Model):
    name = models.CharField("Ten khu vuc", max_length=100)
    description = models.TextField("Mo ta", blank=True, default="")

    latitude = models.FloatField("Vi do", null=True, blank=True)
    longitude = models.FloatField("Kinh do", null=True, blank=True)

    class Meta:
        verbose_name = "Khu vuc"
        verbose_name_plural = "Danh sach khu vuc"

    def __str__(self):
        return self.name


class ParkingLot(models.Model):
    name = models.CharField("Ten bai xe", max_length=100)
    address = models.CharField("Dia chi", max_length=255)
    area = models.ForeignKey(Area, verbose_name="Khu vuc", on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    district = models.CharField(max_length=100, blank=True, default="")
    capacity = models.PositiveIntegerField("Suc chua")
    price_per_hour = models.PositiveIntegerField("Gia mac dinh (khong dung)", default=0)
    is_active = models.BooleanField("Dang hoat dong", default=True)
    revenue = models.PositiveIntegerField("Doanh thu", default=0)

    class Meta:
        verbose_name = "Bai do xe"
        verbose_name_plural = "Danh sach bai do xe"

    def used_slots(self):
        return self.parkinguser_set.filter(is_active=True).count()

    def available_slots(self):
        return max(self.capacity - self.used_slots(), 0)

    def usage_percent(self):
        if self.capacity == 0:
            return 0
        return int((self.used_slots() / self.capacity) * 100)

    def __str__(self):
        return self.name


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("system", "He thong"),
        ("vehicle", "Xe"),
    ]

    user = models.ForeignKey(
        User,
        verbose_name="Nguoi thuc hien",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    action = models.CharField("Hanh dong", max_length=255)
    type = models.CharField("Loai hoat dong", max_length=20, choices=ACTION_CHOICES, default="system")

    created_at = models.DateTimeField("Thoi gian", auto_now_add=True)

    class Meta:
        verbose_name = "Nhat ky hoat dong"
        verbose_name_plural = "Nhat ky hoat dong"
        ordering = ["-created_at"]

    def __str__(self):
        return self.action


class ParkingUser(models.Model):
    VEHICLE_TYPES = [
        ("car", "O to"),
        ("motorbike", "Xe may"),
        ("bike", "Xe dap"),
    ]

    full_name = models.CharField("Ho va ten", max_length=100)
    phone = models.CharField("So dien thoai", max_length=15, unique=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Dia chi", max_length=255, blank=True)

    license_plate = models.CharField("Bien so xe", max_length=20, unique=True)
    vehicle_type = models.CharField("Loai xe", max_length=20, choices=VEHICLE_TYPES)

    parking_lot = models.ForeignKey(
        ParkingLot,
        verbose_name="Bai do xe",
        on_delete=models.CASCADE,
    )

    is_active = models.BooleanField("Dang do", default=True)
    created_at = models.DateTimeField("Thoi gian vao bai", auto_now_add=True)

    class Meta:
        verbose_name = "Nguoi su dung do xe"
        verbose_name_plural = "Danh sach nguoi su dung do xe"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and self.parking_lot.available_slots() <= 0:
            raise ValidationError("Bai xe da het cho")

        super().save(*args, **kwargs)

        if is_new:
            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} vao bai {self.parking_lot.name}",
                type="vehicle",
            )

    def exit_parking(self):
        if self.is_active:
            time_out = timezone.now()
            hours = max(1, int((time_out - self.created_at).total_seconds() // 3600))

            price = ParkingPrice.objects.get(
                parking_lot=self.parking_lot,
                vehicle_type=self.vehicle_type,
            ).price_per_hour

            total_money = hours * price

            self.parking_lot.revenue += total_money
            self.parking_lot.save(update_fields=["revenue"])

            self.is_active = False
            self.save(update_fields=["is_active"])

            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} roi bai {self.parking_lot.name} - {total_money} VND",
                type="vehicle",
            )

    def __str__(self):
        return f"{self.full_name} - {self.license_plate}"


class ParkingPrice(models.Model):
    VEHICLE_CHOICES = [
        ("car", "O to"),
        ("motorbike", "Xe may"),
        ("bike", "Xe dap"),
    ]

    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="Bai do xe",
    )

    vehicle_type = models.CharField(
        "Loai xe",
        max_length=20,
        choices=VEHICLE_CHOICES,
    )

    price_per_hour = models.PositiveIntegerField("Gia / gio (VND)")

    class Meta:
        unique_together = ("parking_lot", "vehicle_type")
        verbose_name = "Gia gui xe"
        verbose_name_plural = "Bang gia gui xe"

    def __str__(self):
        return f"{self.parking_lot.name} - {self.get_vehicle_type_display()}"
