from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from .models import IntroductionPage
from .models import ParkingLot, ParkingRegistrationRequest, ParkingUser


def _apply_input_style(fields):
    for name, field in fields.items():
        current = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (current + " form-control").strip()
        if name == "password":
            field.widget.attrs["autocomplete"] = "current-password"
        if name in {"password1", "new_password1"}:
            field.widget.attrs["autocomplete"] = "new-password"
        if name in {"password2", "new_password2"}:
            field.widget.attrs["autocomplete"] = "new-password"


class PublicLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={"placeholder": "Nhập tên đăng nhập"}),
    )
    password = forms.CharField(
        label="Mật khẩu",
        strip=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Nhập mật khẩu"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_input_style(self.fields)


class PublicRegisterForm(UserCreationForm):
    first_name = forms.CharField(
        label="Họ và tên",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Nhập họ và tên"}),
    )
    username = forms.CharField(
        label="Tên đăng nhập",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Chọn tên đăng nhập"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Nhập email"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Mật khẩu"
        self.fields["password2"].label = "Nhập lại mật khẩu"
        self.fields["password1"].widget.attrs["placeholder"] = "Nhập mật khẩu"
        self.fields["password2"].widget.attrs["placeholder"] = "Nhập lại mật khẩu"
        _apply_input_style(self.fields)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class PublicPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Nhập email đã đăng ký"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_input_style(self.fields)


class PublicSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Mật khẩu mới"
        self.fields["new_password2"].label = "Nhập lại mật khẩu mới"
        self.fields["new_password1"].widget.attrs["placeholder"] = "Nhập mật khẩu mới"
        self.fields["new_password2"].widget.attrs["placeholder"] = "Nhập lại mật khẩu mới"
        _apply_input_style(self.fields)


class ParkingRegistrationRequestForm(forms.ModelForm):
    class Meta:
        model = ParkingRegistrationRequest
        fields = [
            "full_name",
            "phone",
            "email",
            "address",
            "license_plate",
            "vehicle_type",
            "parking_lot",
            "note",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Nhập họ và tên"}),
            "phone": forms.TextInput(attrs={"placeholder": "Nhập số điện thoại"}),
            "email": forms.EmailInput(attrs={"placeholder": "Nhập email để nhận thông báo"}),
            "address": forms.TextInput(attrs={"placeholder": "Nhập địa chỉ hiện tại"}),
            "license_plate": forms.TextInput(attrs={"placeholder": "Nhập biển số xe"}),
            "note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Thêm ghi chú nếu bạn có nhu cầu đặc biệt hoặc thời gian gửi xe dự kiến",
                }
            ),
        }
        labels = {
            "full_name": "Họ và tên",
            "phone": "Số điện thoại",
            "email": "Email",
            "address": "Địa chỉ",
            "license_plate": "Biển số xe",
            "vehicle_type": "Loại xe",
            "parking_lot": "Bãi đỗ muốn đăng ký",
            "note": "Ghi chú thêm",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        _apply_input_style(self.fields)
        self.fields["parking_lot"].queryset = ParkingLot.objects.filter(
            is_deleted=False,
            is_active=True,
        ).order_by("name")
        self.fields["parking_lot"].widget.attrs["class"] = "form-select"
        self.fields["vehicle_type"].widget.attrs["class"] = "form-select"
        self.fields["email"].required = True
        self.fields["note"].required = False

        if user and user.is_authenticated:
            if user.first_name and not self.initial.get("full_name"):
                self.initial["full_name"] = user.first_name
            if user.email and not self.initial.get("email"):
                self.initial["email"] = user.email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if ParkingUser.objects.filter(phone=phone, is_deleted=False).exists():
            raise forms.ValidationError("Số điện thoại này đã có trong danh sách người gửi xe.")
        if ParkingRegistrationRequest.objects.filter(
            phone=phone,
            status=ParkingRegistrationRequest.STATUS_PENDING,
        ).exists():
            raise forms.ValidationError("Số điện thoại này đang có đơn chờ duyệt.")
        return phone

    def clean_license_plate(self):
        license_plate = (self.cleaned_data.get("license_plate") or "").strip().upper()
        if ParkingUser.objects.filter(license_plate__iexact=license_plate, is_deleted=False).exists():
            raise forms.ValidationError("Biển số xe này đã có trong hệ thống.")
        if ParkingRegistrationRequest.objects.filter(
            license_plate__iexact=license_plate,
            status=ParkingRegistrationRequest.STATUS_PENDING,
        ).exists():
            raise forms.ValidationError("Biển số xe này đang có đơn chờ duyệt.")
        return license_plate

class IntroductionPageForm(forms.ModelForm):
    class Meta:
        model = IntroductionPage
        fields = '__all__'