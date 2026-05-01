import csv
from decimal import Decimal
from io import StringIO

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.store import Store, StoreService
from app.schemas import StoreCreate
from app.services.geocoding import geocode_query


CSV_HEADERS = [
    "store_id",
    "name",
    "store_type",
    "status",
    "latitude",
    "longitude",
    "address_street",
    "address_city",
    "address_state",
    "address_postal_code",
    "address_country",
    "phone",
    "services",
    "hours_mon",
    "hours_tue",
    "hours_wed",
    "hours_thu",
    "hours_fri",
    "hours_sat",
    "hours_sun",
]


def parse_services(value: str) -> list[str]:
    if not value:
        return []
    return [service.strip() for service in value.split("|") if service.strip()]


def row_to_store_payload(row: dict[str, str], db: Session) -> StoreCreate:
    latitude = row["latitude"].strip()
    longitude = row["longitude"].strip()
    if not latitude or not longitude:
        address = (
            f"{row['address_street']}, {row['address_city']}, "
            f"{row['address_state']} {row['address_postal_code']}, {row['address_country']}"
        )
        geocoded_latitude, geocoded_longitude = geocode_query(db, "address", address)
        latitude = f"{geocoded_latitude:.6f}"
        longitude = f"{geocoded_longitude:.6f}"

    return StoreCreate(
        store_id=row["store_id"],
        name=row["name"],
        store_type=row["store_type"],
        status=row["status"],
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        address_street=row["address_street"],
        address_city=row["address_city"],
        address_state=row["address_state"],
        address_postal_code=row["address_postal_code"],
        address_country=row["address_country"],
        phone=row["phone"],
        services=parse_services(row["services"]),
        hours={
            "mon": row["hours_mon"],
            "tue": row["hours_tue"],
            "wed": row["hours_wed"],
            "thu": row["hours_thu"],
            "fri": row["hours_fri"],
            "sat": row["hours_sat"],
            "sun": row["hours_sun"],
        },
    )


def validation_errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()]


def upsert_store(db: Session, payload: StoreCreate) -> str:
    store = db.execute(
        select(Store).options(selectinload(Store.services)).where(Store.store_id == payload.store_id)
    ).scalar_one_or_none()

    store_data = payload.model_dump(exclude={"services"})
    store_data["hours"] = payload.hours.model_dump()

    if store is None:
        db.add(Store(**store_data))
        replace_store_services(db, payload.store_id, list(payload.services))
        return "created"

    for field_name, value in store_data.items():
        setattr(store, field_name, value)
    replace_store_services(db, payload.store_id, list(payload.services))
    return "updated"


def replace_store_services(db: Session, store_id: str, services: list[str]) -> None:
    from sqlalchemy import delete

    db.execute(delete(StoreService).where(StoreService.store_id == store_id))
    db.add_all(StoreService(store_id=store_id, service_key=service_key) for service_key in sorted(set(services)))


def validate_and_import_stores_csv(db: Session, csv_text: str) -> dict[str, object]:
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames != CSV_HEADERS:
        return {
            "total_rows_processed": 0,
            "successfully_created": 0,
            "successfully_updated": 0,
            "failed": [
                {
                    "row_number": 1,
                    "store_id": None,
                    "errors": ["CSV headers must match the required columns and order exactly"],
                }
            ],
        }

    parsed_rows: list[StoreCreate] = []
    failures: list[dict[str, object]] = []
    total_rows = 0

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        try:
            parsed_rows.append(row_to_store_payload(row, db))
        except ValidationError as exc:
            failures.append(
                {
                    "row_number": row_number,
                    "store_id": row.get("store_id"),
                    "errors": validation_errors(exc),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "row_number": row_number,
                    "store_id": row.get("store_id"),
                    "errors": [str(exc)],
                }
            )

    if failures:
        return {
            "total_rows_processed": total_rows,
            "successfully_created": 0,
            "successfully_updated": 0,
            "failed": failures,
        }

    created = 0
    updated = 0
    try:
        for payload in parsed_rows:
            result = upsert_store(db, payload)
            if result == "created":
                created += 1
            else:
                updated += 1
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "total_rows_processed": total_rows,
        "successfully_created": created,
        "successfully_updated": updated,
        "failed": [],
    }
