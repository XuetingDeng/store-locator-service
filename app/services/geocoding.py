import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session


def normalize_query(source: str, query: str) -> tuple[str, str]:
    query_text = f"{source}:{query.strip().lower()}"
    return query_text, sha256(query_text.encode("utf-8")).hexdigest()


def get_cached_geocode(db: Session, query_hash: str) -> tuple[float, float] | None:
    row = db.execute(
        text(
            """
            SELECT latitude, longitude
            FROM geocode_cache
            WHERE query_hash = :query_hash
              AND expires_at > now()
            """
        ),
        {"query_hash": query_hash},
    ).first()
    if row is None:
        return None
    return float(row.latitude), float(row.longitude)


def cache_geocode(db: Session, query_hash: str, query_text: str, latitude: float, longitude: float) -> None:
    db.execute(
        text(
            """
            INSERT INTO geocode_cache (query_hash, query_text, latitude, longitude, provider, expires_at)
            VALUES (:query_hash, :query_text, :latitude, :longitude, 'nominatim', :expires_at)
            ON CONFLICT (query_hash) DO UPDATE
            SET latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                provider = EXCLUDED.provider,
                expires_at = EXCLUDED.expires_at,
                created_at = now()
            """
        ),
        {
            "query_hash": query_hash,
            "query_text": query_text,
            "latitude": latitude,
            "longitude": longitude,
            "expires_at": datetime.now(UTC) + timedelta(days=30),
        },
    )
    db.commit()


def geocode_query(db: Session, source: str, query: str) -> tuple[float, float]:
    query_text, query_hash = normalize_query(source, query)
    cached = get_cached_geocode(db, query_hash)
    if cached is not None:
        return cached

    params = urlencode({"q": query, "format": "json", "limit": 1, "countrycodes": "us"})
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "store-locator-service/0.1"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Geocoding provider unavailable") from exc

    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    latitude = float(payload[0]["lat"])
    longitude = float(payload[0]["lon"])
    cache_geocode(db, query_hash, query_text, latitude, longitude)
    return latitude, longitude
