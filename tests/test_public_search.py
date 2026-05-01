def test_public_search_by_coordinates_and_filters(client):
    payload = {"latitude": "28.581300", "longitude": "-81.386200"}

    response = client.post("/api/stores/search?radius_miles=25", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["location"]["source"] == "coordinates"
    assert body["metadata"]["result_count"] > 0
    distances = [item["distance_miles"] for item in body["results"]]
    assert distances == sorted(distances)

    filtered = client.post(
        "/api/stores/search?radius_miles=25&services=pickup&store_types=outlet",
        json=payload,
    )
    assert filtered.status_code == 200
    for item in filtered.json()["results"]:
        assert item["store_type"] == "outlet"
        assert "pickup" in item["services"]


def test_public_search_rejects_invalid_location(client):
    response = client.post("/api/stores/search", json={"latitude": "28.581300"})
    assert response.status_code == 422
