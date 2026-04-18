LIMITED_MANAGER_GROUP = "parking_user_creator"


def is_manager_user(user):
    return bool(
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name=LIMITED_MANAGER_GROUP).exists()
        )
    )
