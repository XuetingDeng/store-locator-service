BEGIN;

CREATE TEMP TABLE staging_stores (
    store_id TEXT,
    name TEXT,
    store_type TEXT,
    status TEXT,
    latitude TEXT,
    longitude TEXT,
    address_street TEXT,
    address_city TEXT,
    address_state TEXT,
    address_postal_code TEXT,
    address_country TEXT,
    phone TEXT,
    services TEXT,
    hours_mon TEXT,
    hours_tue TEXT,
    hours_wed TEXT,
    hours_thu TEXT,
    hours_fri TEXT,
    hours_sat TEXT,
    hours_sun TEXT
) ON COMMIT DROP;

\copy staging_stores FROM 'stores_1000.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO stores (
    store_id,
    name,
    store_type,
    status,
    latitude,
    longitude,
    address_street,
    address_city,
    address_state,
    address_postal_code,
    address_country,
    phone,
    hours,
    updated_at
)
SELECT
    store_id,
    name,
    store_type,
    status,
    latitude::NUMERIC(9, 6),
    longitude::NUMERIC(9, 6),
    address_street,
    address_city,
    address_state,
    address_postal_code,
    address_country,
    phone,
    jsonb_build_object(
        'mon', hours_mon,
        'tue', hours_tue,
        'wed', hours_wed,
        'thu', hours_thu,
        'fri', hours_fri,
        'sat', hours_sat,
        'sun', hours_sun
    ),
    now()
FROM staging_stores
ON CONFLICT (store_id) DO UPDATE
SET name = EXCLUDED.name,
    store_type = EXCLUDED.store_type,
    status = EXCLUDED.status,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    address_street = EXCLUDED.address_street,
    address_city = EXCLUDED.address_city,
    address_state = EXCLUDED.address_state,
    address_postal_code = EXCLUDED.address_postal_code,
    address_country = EXCLUDED.address_country,
    phone = EXCLUDED.phone,
    hours = EXCLUDED.hours,
    updated_at = now();

DELETE FROM store_services
WHERE store_id IN (SELECT store_id FROM staging_stores);

INSERT INTO store_services (store_id, service_key)
SELECT DISTINCT
    s.store_id,
    split_services.service_key
FROM staging_stores s
CROSS JOIN LATERAL regexp_split_to_table(s.services, '\|') AS split_services(service_key)
JOIN services allowed_services ON allowed_services.service_key = split_services.service_key
WHERE split_services.service_key <> ''
ON CONFLICT DO NOTHING;

COMMIT;
