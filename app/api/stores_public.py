from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.admin_stores import serialize_store
from app.core.rate_limit import enforce_public_search_rate_limit
from app.db.session import get_db
from app.models.store import Store, StoreService
from app.schemas import ServiceKey, StoreSearchRequest, StoreSearchResponse, StoreSearchResult, StoreType
from app.services.geocoding import geocode_query
from app.services.search import bounding_box, distance_miles, is_store_open_now

router = APIRouter(prefix="/api/stores", tags=["public stores"])


def resolve_search_location(payload: StoreSearchRequest, db: Session) -> tuple[float, float, str, str | None]:
    if payload.latitude is not None and payload.longitude is not None:
        return float(payload.latitude), float(payload.longitude), "coordinates", None
    if payload.postal_code is not None:
        latitude, longitude = geocode_query(db, "postal_code", payload.postal_code)
        return latitude, longitude, "postal_code", payload.postal_code

    latitude, longitude = geocode_query(db, "address", payload.address or "")
    return latitude, longitude, "address", payload.address


@router.post("/search", response_model=StoreSearchResponse)
def search_stores(
    payload: StoreSearchRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    radius_miles: float = Query(default=10, gt=0, le=100),
    services: list[ServiceKey] = Query(default=[]),
    store_types: list[StoreType] = Query(default=[]),
    open_now: bool = Query(default=False),
) -> StoreSearchResponse:
    enforce_public_search_rate_limit(request, response)
    search_latitude, search_longitude, source, query = resolve_search_location(payload, db)
    min_lat, max_lat, min_lon, max_lon = bounding_box(search_latitude, search_longitude, radius_miles)

    statement = (
        select(Store)
        .options(selectinload(Store.services))
        .where(
            Store.status == "active",
            Store.latitude.between(Decimal(str(min_lat)), Decimal(str(max_lat))),
            Store.longitude.between(Decimal(str(min_lon)), Decimal(str(max_lon))),
        )
        .order_by(Store.store_id)
    )

    if store_types:
        statement = statement.where(Store.store_type.in_(list(store_types)))
    if services:
        statement = (
            statement.join(StoreService)
            .where(StoreService.service_key.in_(list(services)))
            .group_by(Store.store_id)
            .having(func.count(StoreService.service_key.distinct()) == len(set(services)))
        )

    stores = db.execute(statement).scalars().all()
    results: list[StoreSearchResult] = []
    for store in stores:
        distance = distance_miles(search_latitude, search_longitude, float(store.latitude), float(store.longitude))
        if distance > radius_miles:
            continue

        store_is_open = is_store_open_now(store.hours)
        if open_now and not store_is_open:
            continue

        base = serialize_store(store).model_dump()
        results.append(StoreSearchResult(**base, distance_miles=round(distance, 2), is_open_now=store_is_open))

    results.sort(key=lambda item: item.distance_miles)

    return StoreSearchResponse(
        metadata={
            "location": {
                "latitude": search_latitude,
                "longitude": search_longitude,
                "source": source,
                "query": query,
            },
            "radius_miles": radius_miles,
            "services": list(services),
            "store_types": list(store_types),
            "open_now": open_now,
            "result_count": len(results),
        },
        results=results,
    )
