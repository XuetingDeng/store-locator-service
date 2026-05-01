from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.store import Store, StoreService
from app.models.user import User
from app.schemas import StoreCreate, StoreImportReport, StoreListResponse, StoreResponse, StoreUpdate
from app.services.csv_import import validate_and_import_stores_csv

router = APIRouter(prefix="/api/admin/stores", tags=["admin stores"])


def serialize_store(store: Store) -> StoreResponse:
    services = sorted(store_service.service_key for store_service in store.services)
    return StoreResponse(
        store_id=store.store_id,
        name=store.name,
        store_type=store.store_type,
        status=store.status,
        latitude=store.latitude,
        longitude=store.longitude,
        address_street=store.address_street,
        address_city=store.address_city,
        address_state=store.address_state,
        address_postal_code=store.address_postal_code,
        address_country=store.address_country,
        phone=store.phone,
        services=services,
        hours=store.hours,
    )


def replace_store_services(db: Session, store_id: str, services: list[str]) -> None:
    db.execute(delete(StoreService).where(StoreService.store_id == store_id))
    db.add_all(StoreService(store_id=store_id, service_key=service_key) for service_key in sorted(set(services)))


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:write")),
) -> StoreResponse:
    existing_store = db.get(Store, payload.store_id)
    if existing_store is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store already exists")

    store_data = payload.model_dump(exclude={"services"})
    store_data["hours"] = payload.hours.model_dump()
    store = Store(**store_data)
    db.add(store)
    replace_store_services(db, payload.store_id, list(payload.services))
    db.commit()
    db.refresh(store)

    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == payload.store_id)
    ).scalar_one()
    return serialize_store(store)


@router.get("", response_model=StoreListResponse)
def list_stores(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:read")),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StoreListResponse:
    total = db.execute(select(func.count()).select_from(Store)).scalar_one()
    stores = db.execute(
        select(Store)
        .options(selectinload(Store.services))
        .order_by(Store.store_id)
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return StoreListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[serialize_store(store) for store in stores],
    )


@router.post("/import", response_model=StoreImportReport)
async def import_stores(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:import")),
) -> StoreImportReport:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload must be a CSV file")

    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8 encoded") from exc

    report = validate_and_import_stores_csv(db, csv_text)
    if report["failed"]:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=report)
    return StoreImportReport(**report)


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:read")),
) -> StoreResponse:
    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == store_id)
    ).scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return serialize_store(store)


@router.patch("/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: str,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:write")),
) -> StoreResponse:
    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == store_id)
    ).scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    update_data = payload.model_dump(exclude_unset=True)
    services = update_data.pop("services", None)
    if "hours" in update_data:
        update_data["hours"] = payload.hours.model_dump() if payload.hours else None

    for field_name, value in update_data.items():
        setattr(store, field_name, value)
    store.updated_at = datetime.now(UTC)

    if services is not None:
        replace_store_services(db, store_id, services)

    db.commit()
    db.expire_all()
    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == store_id)
    ).scalar_one()
    return serialize_store(store)


@router.delete("/{store_id}", response_model=StoreResponse)
def deactivate_store(
    store_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stores:delete")),
) -> StoreResponse:
    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == store_id)
    ).scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    store.status = "inactive"
    store.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(store)
    return serialize_store(store)
