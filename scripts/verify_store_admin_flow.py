import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.store import Store, StoreService


BASE_URL = "http://127.0.0.1:8000"
TEST_STORE_ID = "S9999"


def request(method: str, path: str, payload: dict[str, object] | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def login(email: str) -> str:
    status, payload = request(
        "POST",
        "/api/auth/login",
        {"email": email, "password": "TestPassword123!"},
    )
    assert_status(f"{email} login", status, 200)
    return payload["access_token"]


def assert_status(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")
    print(f"{label}: {actual}")


def cleanup_database() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(StoreService).where(StoreService.store_id == TEST_STORE_ID))
        db.execute(delete(Store).where(Store.store_id == TEST_STORE_ID))
        db.commit()
    finally:
        db.close()


def main() -> None:
    admin_token = login("admin@test.com")
    viewer_token = login("viewer@test.com")

    cleanup_database()

    status, stores = request("GET", "/api/admin/stores?limit=2&offset=0", token=admin_token)
    assert_status("admin list stores", status, 200)
    assert stores["total"] >= 1000
    assert len(stores["items"]) == 2

    test_store = {
        "store_id": TEST_STORE_ID,
        "name": "Integration Test Store",
        "store_type": "regular",
        "status": "active",
        "latitude": "42.360100",
        "longitude": "-71.058900",
        "address_street": "1 Test Way",
        "address_city": "Boston",
        "address_state": "MA",
        "address_postal_code": "02101",
        "address_country": "USA",
        "phone": "617-555-0199",
        "services": ["pickup", "returns"],
        "hours": {
            "mon": "08:00-20:00",
            "tue": "08:00-20:00",
            "wed": "08:00-20:00",
            "thu": "08:00-20:00",
            "fri": "08:00-21:00",
            "sat": "09:00-18:00",
            "sun": "closed",
        },
    }

    status, created = request("POST", "/api/admin/stores", test_store, token=admin_token)
    assert_status("admin create store", status, 201)
    assert created["store_id"] == TEST_STORE_ID

    status, duplicate = request("POST", "/api/admin/stores", test_store, token=admin_token)
    assert_status("duplicate create denied", status, 409)

    status, fetched = request("GET", f"/api/admin/stores/{TEST_STORE_ID}", token=admin_token)
    assert_status("admin get store", status, 200)
    assert fetched["services"] == ["pickup", "returns"]

    status, updated = request(
        "PATCH",
        f"/api/admin/stores/{TEST_STORE_ID}",
        {"name": "Updated Test Store", "services": ["pickup"], "phone": "617-555-0101"},
        token=admin_token,
    )
    assert_status("admin patch store", status, 200)
    assert updated["name"] == "Updated Test Store"
    assert updated["services"] == ["pickup"]

    status, _ = request(
        "PATCH",
        f"/api/admin/stores/{TEST_STORE_ID}",
        {"latitude": "10.000000"},
        token=admin_token,
    )
    assert_status("forbidden patch field rejected", status, 422)

    status, _ = request(
        "PATCH",
        f"/api/admin/stores/{TEST_STORE_ID}",
        {"name": "Viewer Should Fail"},
        token=viewer_token,
    )
    assert_status("viewer patch denied", status, 403)

    status, deactivated = request("DELETE", f"/api/admin/stores/{TEST_STORE_ID}", token=admin_token)
    assert_status("admin deactivate store", status, 200)
    assert deactivated["status"] == "inactive"

    cleanup_database()


if __name__ == "__main__":
    main()
