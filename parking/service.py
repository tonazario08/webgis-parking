from .models import ParkingUser, ParkingPrice


def calculate_total_revenue():
    """
    Tính tổng doanh thu hiện tại
    = tổng giá theo loại xe + bãi xe của các xe đang đỗ
    """
    total = 0

    users = ParkingUser.objects.filter(is_active=True)

    for user in users:
        try:
            price = ParkingPrice.objects.get(
                parking_lot=user.parking_lot,
                vehicle_type=user.vehicle_type
            )
            total += price.price_per_hour
        except ParkingPrice.DoesNotExist:
            # nếu bãi xe chưa khai báo giá cho loại xe này
            pass

    return total
