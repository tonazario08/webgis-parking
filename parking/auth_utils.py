NHAN_VIEN_GROUP = "nhan_vien"


def is_admin(user):
    """Admin: is_superuser hoặc is_staff."""
    return bool(user.is_authenticated and (user.is_superuser or user.is_staff))


def is_nhan_vien(user):
    """Nhân viên: thuộc group nhan_vien, không phải admin."""
    return bool(
        user.is_authenticated
        and not is_admin(user)
        and user.groups.filter(name=NHAN_VIEN_GROUP).exists()
    )


def is_manager_user(user):
    """Bất kỳ ai có thể vào khu quản trị (admin hoặc nhân viên)."""
    return is_admin(user) or is_nhan_vien(user)
