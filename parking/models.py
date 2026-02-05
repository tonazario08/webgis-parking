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

    # GPS coordinates (for GIS features)
    latitude = models.FloatField("Vĩ độ", null=True, blank=True)
    longitude = models.FloatField("Kinh độ", null=True, blank=True)

    capacity = models.IntegerField("Sức chứa")
    price_per_hour = models.IntegerField("Giá/giờ")
    is_active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        verbose_name = "Bãi đỗ xe"
        verbose_name_plural = "Danh sách bãi đỗ xe"

    def used_slots(self):
        return self.parkinguser_set.filter(is_active=True).count()

    @property
    def available_slots(self):
        """Số chỗ trống hiện tại (property để tương thích với utils)."""
        return self.capacity - self.used_slots()

    @property
    def total_slots(self):
        return self.capacity

    def is_full(self):
        return self.available_slots <= 0

    def is_nearly_full(self):
        if self.capacity == 0:
            return False
        return (self.available_slots / self.capacity) < 0.15

    def get_capacity_percent(self):
        if self.capacity == 0:
            return 0
        used = self.capacity - self.available_slots
        return int((used / self.capacity) * 100)

    def get_status(self):
        # Placeholder: can be extended to return an object/dict with name/color
        return None

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

    # 👉 Trường thời gian (đóng vai trò created_at)
    created_at = models.DateTimeField(
        "Thời gian",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Nhật ký hoạt động"
        verbose_name_plural = "Nhật ký hoạt động"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action}"


# ========================
# 4. Người sử dụng đỗ xe
# ========================
class ParkingUser(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Ô tô'),
        ('motorbike', 'Xe máy'),
        ('bike', 'Xe đạp'),
    ]

    full_name = models.CharField("Họ và tên", max_length=100)
    phone = models.CharField("Số điện thoại", max_length=15)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)

    license_plate = models.CharField("Biển số xe", max_length=20)
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
        if self.pk is None:
            if self.parking_lot.available_slots <= 0:
                raise ValueError("Bãi xe đã hết chỗ")

            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} vào bãi {self.parking_lot.name}",
                type='vehicle'
            )

        super().save(*args, **kwargs)

    def exit_parking(self):
        if self.is_active:
            self.is_active = False
            self.save()

            ActivityLog.objects.create(
                action=f"Xe {self.license_plate} rời bãi {self.parking_lot.name}",
                type='vehicle'
            )

    def __str__(self):
        return f"{self.full_name} - {self.license_plate}"
