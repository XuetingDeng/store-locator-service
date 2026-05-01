import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.user import User


BASE_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "api-user-test@test.com"


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


def assert_status(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")
    print(f"{label}: {actual}")


def login(email: str, password: str = "TestPassword123!") -> str:
    status, payload = request("POST", "/api/auth/login", {"email": email, "password": password})
    assert_status(f"{email} login", status, 200)
    return payload["access_token"]


def cleanup_database() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.email == TEST_EMAIL))
        db.commit()
    finally:
        db.close()


def main() -> None:
    cleanup_database()
    admin_token = login("admin@test.com")
    marketer_token = login("marketer@test.com")

    status, users = request("GET", "/api/admin/users?limit=10", token=admin_token)
    assert_status("admin list users", status, 200)
    assert users["total"] >= 3

    status, created = request(
        "POST",
        "/api/admin/users",
        {
            "email": TEST_EMAIL,
            "password": "CreatedPassword123!",
            "role": "viewer",
            "status": "active",
            "must_change_password": True,
        },
        token=admin_token,
    )
    assert_status("admin create user", status, 201)
    user_id = created["user_id"]
    assert created["role"] == "viewer"

    login(TEST_EMAIL, "CreatedPassword123!")

    status, duplicate = request(
        "POST",
        "/api/admin/users",
        {"email": TEST_EMAIL, "password": "CreatedPassword123!", "role": "viewer"},
        token=admin_token,
    )
    assert_status("duplicate email denied", status, 409)

    status, updated = request(
        "PUT",
        f"/api/admin/users/{user_id}",
        {"role": "marketer", "must_change_password": False},
        token=admin_token,
    )
    assert_status("admin update user", status, 200)
    assert updated["role"] == "marketer"
    assert updated["must_change_password"] is False

    status, _ = request("GET", "/api/admin/users", token=marketer_token)
    assert_status("marketer list users denied", status, 403)

    status, deleted = request("DELETE", f"/api/admin/users/{user_id}", token=admin_token)
    assert_status("admin deactivate user", status, 200)
    assert deleted["status"] == "inactive"

    cleanup_database()


if __name__ == "__main__":
    main()
