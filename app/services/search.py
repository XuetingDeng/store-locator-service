from datetime import datetime
from math import cos, radians

from geopy.distance import geodesic


DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def bounding_box(latitude: float, longitude: float, radius_miles: float) -> tuple[float, float, float, float]:
    latitude_delta = radius_miles / 69.0
    longitude_delta = radius_miles / (69.0 * cos(radians(latitude)))
    return (
        latitude - latitude_delta,
        latitude + latitude_delta,
        longitude - longitude_delta,
        longitude + longitude_delta,
    )


def distance_miles(origin_latitude: float, origin_longitude: float, latitude: float, longitude: float) -> float:
    return geodesic((origin_latitude, origin_longitude), (latitude, longitude)).miles


def parse_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def is_store_open_now(hours: dict[str, str], now: datetime | None = None) -> bool:
    current_time = now or datetime.now()
    day_key = DAY_KEYS[current_time.weekday()]
    hours_value = hours.get(day_key, "closed")
    if hours_value == "closed":
        return False

    open_time, close_time = hours_value.split("-")
    current_minutes = current_time.hour * 60 + current_time.minute
    return parse_minutes(open_time) <= current_minutes < parse_minutes(close_time)
