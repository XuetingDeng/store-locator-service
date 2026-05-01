from tests.conftest import auth_header, login


def test_user_management_admin_only(client, db_cleanup):
    admin_token = login(client, "admin@test.com")
    marketer_token = login(client, "marketer@test.com")

    listed = client.get("/api/admin/users", headers=auth_header(admin_token))
    assert listed.status_code == 200
    assert listed.json()["total"] >= 3

    created = client.post(
        "/api/admin/users",
        json={
            "email": "pytest-user@test.com",
            "password": "CreatedPassword123!",
            "role": "viewer",
            "status": "active",
        },
        headers=auth_header(admin_token),
    )
    assert created.status_code == 201
    user_id = created.json()["user_id"]

    assert login(client, "pytest-user@test.com", "CreatedPassword123!")

    updated = client.put(
        f"/api/admin/users/{user_id}",
        json={"role": "marketer", "must_change_password": False},
        headers=auth_header(admin_token),
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "marketer"

    denied = client.get("/api/admin/users", headers=auth_header(marketer_token))
    assert denied.status_code == 403

    deleted = client.delete(f"/api/admin/users/{user_id}", headers=auth_header(admin_token))
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"
