from django.db.utils import OperationalError, ProgrammingError

from .auth_utils import is_manager_user
from .models import ParkingRegistrationRequest


def auth_navigation(request):
    pending_registration_count = 0
    if is_manager_user(request.user):
        try:
            pending_registration_count = ParkingRegistrationRequest.objects.filter(
                status=ParkingRegistrationRequest.STATUS_PENDING
            ).count()
        except (OperationalError, ProgrammingError):
            pending_registration_count = 0

    return {
        "is_manager_user": is_manager_user(request.user),
        "pending_registration_count": pending_registration_count,
    }
