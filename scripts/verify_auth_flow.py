import json
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


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


def main() -> None:
    status, admin_login = request(
        "POST",
        "/api/auth/login",
        {"email": "admin@test.com", "password": "TestPassword123!"},
    )
    assert_status("admin login", status, 200)

    admin_access = admin_login["access_token"]
    admin_refresh = admin_login["refresh_token"]

    status, me = request("GET", "/api/auth/me", token=admin_access)
    assert_status("admin /me", status, 200)
    assert me["role"] == "admin"

    status, _ = request("GET", "/api/debug/rbac/users-write", token=admin_access)
    assert_status("admin users:write", status, 200)

    status, _ = request("POST", "/api/auth/refresh", {"refresh_token": admin_refresh})
    assert_status("refresh before logout", status, 200)

    status, _ = request("POST", "/api/auth/logout", {"refresh_token": admin_refresh})
    assert_status("logout", status, 200)

    status, _ = request("POST", "/api/auth/refresh", {"refresh_token": admin_refresh})
    assert_status("refresh after logout", status, 401)

    status, viewer_login = request(
        "POST",
        "/api/auth/login",
        {"email": "viewer@test.com", "password": "TestPassword123!"},
    )
    assert_status("viewer login", status, 200)

    viewer_access = viewer_login["access_token"]
    status, _ = request("GET", "/api/debug/rbac/stores-read", token=viewer_access)
    assert_status("viewer stores:read", status, 200)

    status, _ = request("GET", "/api/debug/rbac/users-write", token=viewer_access)
    assert_status("viewer users:write denied", status, 403)

    status, _ = request("GET", "/api/auth/me")
    assert_status("missing token denied", status, 401)


if __name__ == "__main__":
    main()
