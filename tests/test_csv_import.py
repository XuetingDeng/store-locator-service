from tests.conftest import auth_header, login


CSV_CONTENT = """store_id,name,store_type,status,latitude,longitude,address_street,address_city,address_state,address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun
S9998,Import Test Store,regular,active,42.360100,-71.058900,1 Import Way,Boston,MA,02101,USA,617-555-0111,pickup|returns,08:00-20:00,08:00-20:00,08:00-20:00,08:00-20:00,08:00-21:00,09:00-18:00,closed
"""


def test_csv_import_create_and_update(client, db_cleanup):
    admin_token = login(client, "admin@test.com")
    files = {"file": ("stores.csv", CSV_CONTENT, "text/csv")}

    created = client.post("/api/admin/stores/import", files=files, headers=auth_header(admin_token))
    assert created.status_code == 200
    assert created.json()["successfully_created"] == 1

    updated = client.post("/api/admin/stores/import", files=files, headers=auth_header(admin_token))
    assert updated.status_code == 200
    assert updated.json()["successfully_updated"] == 1


def test_csv_import_rejects_bad_rows(client, db_cleanup):
    admin_token = login(client, "admin@test.com")
    bad_csv = CSV_CONTENT.replace("regular", "bad_type")
    files = {"file": ("stores.csv", bad_csv, "text/csv")}

    response = client.post("/api/admin/stores/import", files=files, headers=auth_header(admin_token))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["failed"][0]["row_number"] == 2
