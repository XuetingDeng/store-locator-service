from datetime import datetime

from app.core.security import hash_password, verify_password
from app.schemas import StoreHours
from app.services.search import bounding_box, distance_miles, is_store_open_now


def test_password_hash_and_verify():
    password_hash = hash_password("SecretPassword123!")
    assert verify_password("SecretPassword123!", password_hash)
    assert not verify_password("WrongPassword123!", password_hash)


def test_bounding_box_and_distance():
    min_lat, max_lat, min_lon, max_lon = bounding_box(42.3601, -71.0589, 10)
    assert min_lat < 42.3601 < max_lat
    assert min_lon < -71.0589 < max_lon
    assert distance_miles(42.3601, -71.0589, 42.3601, -71.0589) == 0


def test_hours_validation_and_open_now():
    hours = StoreHours(
        mon="08:00-20:00",
        tue="08:00-20:00",
        wed="08:00-20:00",
        thu="08:00-20:00",
        fri="08:00-20:00",
        sat="closed",
        sun="closed",
    )
    assert hours.mon == "08:00-20:00"
    assert is_store_open_now(hours.model_dump(), datetime(2026, 5, 1, 10, 0))
    assert not is_store_open_now(hours.model_dump(), datetime(2026, 5, 1, 21, 0))
