from django.db import models
from django.contrib.auth.models import User


# ========================
# 1. Khu vực
# ========================
class Area(models.Model):
    name = models.CharField("Tên khu vực", max_length=100)
    description = models.TextField("Mô tả", blank=True)

    latitude = models.FloatField("Vĩ độ", null=True, blank=True)
    longitude = models.FloatField("Kinh độ", null=True, blank=True)

    class Meta:
        verbose_name = "Khu vực"
        verbose_name_plural = "Danh sách khu vực"

    def __str__(self):
        return self.name


# ========================
# 2. Bãi đỗ xe
# ========================
class ParkingLot(models.Model):
    name = models.CharField("Tên bãi xe", max_length=100)
    address = models.CharField("Địa chỉ", max_length=255)
    area = models.ForeignKey(Area, verbose_name="Khu vực", on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    district = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField("Sức chứa")
    price_per_hour = models.PositiveIntegerField("Giá mặc định (không dùng)", default=0)
    is_active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        verbose_name = "Bãi đỗ xe"
        verbose_name_plural = "Danh sách bãi đỗ xe"

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


# ========================
# 3. Nhật ký hoạt động
# ========================
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('system', 'Hệ thống'),
        ('vehicle', 'Xe'),
    ]

    user = models.ForeignKey(
        User,
        verbose_name="Người thực hiện",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField("Hành động", max_length=255)
    type = models.CharField("Loại hoạt động", max_length=20, choices=ACTION_CHOICES)

    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        verbose_name = "Nhật ký hoạt động"
        verbose_name_plural = "Nhật ký hoạt động"
        ordering = ['-created_at']

    def __str__(self):
        return self.action


# ========================
# 4. Người sử dụng đỗ xe
# ========================
from django.core.exceptions import ValidationError

class ParkingUser(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Ô tô'),
        ('motorbike', 'Xe máy'),
        ('bike', 'Xe đạp'),
    ]

    full_name = models.CharField("Họ và tên", max_length=100)
    phone = models.CharField("Số điện thoại", max_length=15, unique=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)

    license_plate = models.CharField("Biển số xe", max_length=20, unique=True)
    vehicle_type = models.CharField("Loại xe", max_length=20, choices=VEHICLE_TYPES)

    parking_lot = models.ForeignKey(
        ParkingLot,
        verbose_name="Bãi đỗ xe",
        on_delete=models.CASCADE
    )

    is_active = models.BooleanField("Đang đỗ", default=True)
    created_at = models.DateTimeField("Thời gian vào bãi", auto_now_add=True)

    class Meta:
        verbose_name = "Người sử dụng đỗ xe"
        verbose_name_plural = "Danh sách người sử dụng đỗ xe"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and self.parking_lot.available_slots() <= 0:
            raise ValidationError("Bãi xe đã hết chỗ")

        super().save(*args, **kwargs)

        if is_new:
            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} vào bãi {self.parking_lot.name}",
                type='vehicle'
            )

    def exit_parking(self):
        if self.is_active:
            self.is_active = False
            self.save(update_fields=['is_active'])

            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} rời bãi {self.parking_lot.name}",
                type='vehicle'
            )

    def __str__(self):
        return f"{self.full_name} - {self.license_plate}"



# ========================
# 5. Bảng giá gửi xe
# ========================
class ParkingPrice(models.Model):
    VEHICLE_CHOICES = [
        ('car', 'Ô tô'),
        ('motorbike', 'Xe máy'),
        ('bike', 'Xe đạp'),
    ]

    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name="Bãi đỗ xe"
    )

    vehicle_type = models.CharField(
        "Loại xe",
        max_length=20,
        choices=VEHICLE_CHOICES
    )

    price_per_hour = models.PositiveIntegerField("Giá / giờ (VNĐ)")

    class Meta:
        unique_together = ('parking_lot', 'vehicle_type')
        verbose_name = "Giá gửi xe"
        verbose_name_plural = "Bảng giá gửi xe"

    def __str__(self):
        return f"{self.parking_lot.name} - {self.get_vehicle_type_display()}"
