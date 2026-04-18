from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

VEHICLE_TYPE_CHOICES = [
    ("car", "Ô tô"),
    ("motorbike", "Xe máy"),
    ("bike", "Xe đạp"),
]


class Area(models.Model):
    name = models.CharField("Tên khu vực", max_length=100)
    description = models.TextField("Mô tả", blank=True, default="")
    latitude = models.FloatField("Vĩ độ", null=True, blank=True)
    longitude = models.FloatField("Kinh độ", null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Khu vực"
        verbose_name_plural = "Danh sách khu vực"

    def __str__(self):
        return self.name


class ParkingLot(models.Model):
    name = models.CharField("Tên bãi xe", max_length=100)
    address = models.CharField("Địa chỉ", max_length=255)
    short_description = models.CharField("Mô tả ngắn", max_length=255, blank=True, default="")
    long_description = models.TextField("Mô tả chi tiết", blank=True, default="")
    area = models.ForeignKey(Area, verbose_name="Khu vực", on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    district = models.CharField(max_length=100, blank=True, default="")
    capacity = models.PositiveIntegerField("Sức chứa")
    price_per_hour = models.PositiveIntegerField("Giá mặc định (không dùng)", default=0)
    is_active = models.BooleanField("Đang hoạt động", default=True)
    revenue = models.PositiveIntegerField("Doanh thu", default=0)
    polygon_geojson = models.TextField("Ranh giới (GeoJSON)", blank=True, default="")
    area_sq_m = models.FloatField("Dien tich (m2)", default=0)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Bãi đỗ xe"
        verbose_name_plural = "Danh sách bãi đỗ xe"

    def used_slots(self):
        return self.parkinguser_set.filter(is_active=True, is_deleted=False).count()

    def available_slots(self):
        return max(self.capacity - self.used_slots(), 0)

    def usage_percent(self):
        if self.capacity == 0:
            return 0
        return int((self.used_slots() / self.capacity) * 100)

    def __str__(self):
        return self.name

    def primary_image(self):
        images = list(self.images.all())
        return images[0] if images else None


class ParkingLotImage(models.Model):
    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Bãi đỗ xe",
    )
    image = models.FileField(
        "Hình ảnh",
        upload_to="parking_images/",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"])],
    )
    created_at = models.DateTimeField("Thời gian tạo", auto_now_add=True)

    class Meta:
        verbose_name = "Hình ảnh bãi đỗ xe"
        verbose_name_plural = "Hình ảnh bãi đỗ xe"
        ordering = ["id"]

    def __str__(self):
        return f"Anh {self.parking_lot.name} #{self.pk}"


class ParkingRegistrationRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Chờ duyệt"),
        (STATUS_APPROVED, "Đã duyệt"),
        (STATUS_REJECTED, "Không duyệt"),
    ]

    full_name = models.CharField("Họ và tên", max_length=100)
    phone = models.CharField("Số điện thoại", max_length=15)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)
    license_plate = models.CharField("Biển số xe", max_length=20)
    vehicle_type = models.CharField("Loại xe", max_length=20, choices=VEHICLE_TYPE_CHOICES)
    parking_lot = models.ForeignKey(
        ParkingLot,
        verbose_name="Bãi đỗ xe mong muốn",
        on_delete=models.CASCADE,
        related_name="registration_requests",
    )
    note = models.TextField("Ghi chú", blank=True, default="")
    status = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    reviewed_note = models.CharField("Ghi chú duyệt", max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        User,
        verbose_name="Tài khoản gửi đơn",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parking_registration_requests",
    )
    reviewed_by = models.ForeignKey(
        User,
        verbose_name="Người xử lý",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_parking_registration_requests",
    )
    reviewed_at = models.DateTimeField("Thời gian xử lý", null=True, blank=True)
    created_at = models.DateTimeField("Thời gian gửi", auto_now_add=True)

    class Meta:
        verbose_name = "Đơn đăng ký gửi xe"
        verbose_name_plural = "Đơn đăng ký gửi xe"
        ordering = ["status", "-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.license_plate} ({self.get_status_display()})"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("system", "Hệ thống"),
        ("vehicle", "Xe"),
    ]

    user = models.ForeignKey(
        User,
        verbose_name="Người thực hiện",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    action = models.CharField("Hành động", max_length=255)
    type = models.CharField("Loại hoạt động", max_length=20, choices=ACTION_CHOICES, default="system")

    created_at = models.DateTimeField("Thời gian", auto_now_add=True)

    class Meta:
        verbose_name = "Nhật ký hoạt động"
        verbose_name_plural = "Nhật ký hoạt động"
        ordering = ["-created_at"]

    def __str__(self):
        return self.action


class ParkingUser(models.Model):
    VEHICLE_TYPES = VEHICLE_TYPE_CHOICES

    full_name = models.CharField("Họ và tên", max_length=100)
    phone = models.CharField("Số điện thoại", max_length=15, unique=True)
    email = models.EmailField("Email", blank=True)
    email_verified = models.BooleanField("Email đã xác thực", default=False)
    email_verification_token = models.CharField("Email token", max_length=64, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField("Thời gian gửi xác thực", null=True, blank=True)
    address = models.CharField("Địa chỉ", max_length=255, blank=True)

    license_plate = models.CharField("Biển số xe", max_length=20, unique=True)
    vehicle_type = models.CharField("Loại xe", max_length=20, choices=VEHICLE_TYPES)

    parking_lot = models.ForeignKey(
        ParkingLot,
        verbose_name="Bãi đỗ xe",
        on_delete=models.CASCADE,
    )

    is_active = models.BooleanField("Đang đỗ", default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
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
        ("car", "Ô tô"),
        ("motorbike", "Xe máy"),
        ("bike", "Xe đạp"),
    ]

    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="Bãi đỗ xe",
    )

    vehicle_type = models.CharField(
        "Loại xe",
        max_length=20,
        choices=VEHICLE_CHOICES,
    )

    price_per_hour = models.PositiveIntegerField("Giá / giờ (VND)")

    class Meta:
        unique_together = ("parking_lot", "vehicle_type")
        verbose_name = "Giá gửi xe"
        verbose_name_plural = "Bảng giá gửi xe"

    def __str__(self):
        return f"{self.parking_lot.name} - {self.get_vehicle_type_display()}"

