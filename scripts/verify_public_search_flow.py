import json
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def post_search(payload: dict[str, object], params: dict[str, object] | None = None) -> tuple[int, dict]:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        f"{BASE_URL}/api/stores/search{query}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
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
    payload = {"latitude": "28.581300", "longitude": "-81.386200"}

    status, response = post_search(payload, {"radius_miles": 25})
    assert_status("coordinate search", status, 200)
    assert response["metadata"]["location"]["source"] == "coordinates"
    assert response["metadata"]["result_count"] > 0
    distances = [item["distance_miles"] for item in response["results"]]
    assert distances == sorted(distances)

    status, filtered = post_search(
        payload,
        {"radius_miles": 25, "services": ["pickup"], "store_types": ["outlet"]},
    )
    assert_status("filtered coordinate search", status, 200)
    assert filtered["metadata"]["services"] == ["pickup"]
    assert filtered["metadata"]["store_types"] == ["outlet"]
    assert filtered["metadata"]["result_count"] > 0
    for item in filtered["results"]:
        assert item["status"] == "active"
        assert item["store_type"] == "outlet"
        assert "pickup" in item["services"]

    status, invalid = post_search({"latitude": "28.581300"})
    assert_status("invalid location rejected", status, 422)


if __name__ == "__main__":
    main()
