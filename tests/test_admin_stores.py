from tests.conftest import auth_header, login


def store_payload(store_id: str = "S9999") -> dict:
    return {
        "store_id": store_id,
        "name": "Pytest Store",
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


def test_store_crud_and_permissions(client, db_cleanup):
    admin_token = login(client, "admin@test.com")
    viewer_token = login(client, "viewer@test.com")

    created = client.post("/api/admin/stores", json=store_payload(), headers=auth_header(admin_token))
    assert created.status_code == 201

    listed = client.get("/api/admin/stores?limit=2", headers=auth_header(admin_token))
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1000

    patched = client.patch(
        "/api/admin/stores/S9999",
        json={"name": "Updated Pytest Store", "services": ["pickup"]},
        headers=auth_header(admin_token),
    )
    assert patched.status_code == 200
    assert patched.json()["services"] == ["pickup"]

    forbidden_field = client.patch("/api/admin/stores/S9999", json={"latitude": "10.000000"}, headers=auth_header(admin_token))
    assert forbidden_field.status_code == 422

    viewer_patch = client.patch("/api/admin/stores/S9999", json={"name": "Nope"}, headers=auth_header(viewer_token))
    assert viewer_patch.status_code == 403

    deleted = client.delete("/api/admin/stores/S9999", headers=auth_header(admin_token))
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"
