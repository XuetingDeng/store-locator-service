from tests.conftest import auth_header, login


def test_login_refresh_logout_and_rbac(client):
    response = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "TestPassword123!"})
    assert response.status_code == 200
    tokens = response.json()

    me = client.get("/api/auth/me", headers=auth_header(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200

    logout = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 200

    refresh_after_logout = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_after_logout.status_code == 401

    viewer_token = login(client, "viewer@test.com")
    denied = client.get("/api/debug/rbac/users-write", headers=auth_header(viewer_token))
    assert denied.status_code == 403
