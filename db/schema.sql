BEGIN;

CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(32) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(16) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    must_change_password BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(16) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(5) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    store_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    address_street VARCHAR(255) NOT NULL,
    address_city VARCHAR(120) NOT NULL,
    address_state CHAR(2) NOT NULL,
    address_postal_code CHAR(5) NOT NULL,
    address_country CHAR(3) NOT NULL DEFAULT 'USA',
    phone VARCHAR(12) NOT NULL,
    hours JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT stores_store_id_format CHECK (store_id ~ '^S[0-9]{4}$'),
    CONSTRAINT stores_store_type_check CHECK (store_type IN ('flagship', 'regular', 'outlet', 'express')),
    CONSTRAINT stores_status_check CHECK (status IN ('active', 'inactive', 'temporarily_closed')),
    CONSTRAINT stores_latitude_check CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT stores_longitude_check CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT stores_state_format CHECK (address_state ~ '^[A-Z]{2}$'),
    CONSTRAINT stores_postal_code_format CHECK (address_postal_code ~ '^[0-9]{5}$'),
    CONSTRAINT stores_country_format CHECK (address_country ~ '^[A-Z]{3}$'),
    CONSTRAINT stores_phone_format CHECK (phone ~ '^[0-9]{3}-[0-9]{3}-[0-9]{4}$')
);

CREATE TABLE IF NOT EXISTS services (
    service_key VARCHAR(32) PRIMARY KEY,
    display_name VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS store_services (
    store_id VARCHAR(5) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    service_key VARCHAR(32) NOT NULL REFERENCES services(service_key),
    PRIMARY KEY (store_id, service_key)
);

CREATE TABLE IF NOT EXISTS geocode_cache (
    query_hash CHAR(64) PRIMARY KEY,
    query_text TEXT NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT geocode_cache_latitude_check CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT geocode_cache_longitude_check CHECK (longitude BETWEEN -180 AND 180)
);

CREATE INDEX IF NOT EXISTS idx_stores_latitude_longitude ON stores(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_stores_active ON stores(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_stores_status ON stores(status);
CREATE INDEX IF NOT EXISTS idx_stores_store_type ON stores(store_type);
CREATE INDEX IF NOT EXISTS idx_stores_address_postal_code ON stores(address_postal_code);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_geocode_cache_expires_at ON geocode_cache(expires_at);

INSERT INTO services (service_key, display_name) VALUES
    ('pharmacy', 'Pharmacy'),
    ('pickup', 'Pickup'),
    ('returns', 'Returns'),
    ('optical', 'Optical'),
    ('photo_printing', 'Photo Printing'),
    ('gift_wrapping', 'Gift Wrapping'),
    ('automotive', 'Automotive'),
    ('garden_center', 'Garden Center')
ON CONFLICT (service_key) DO UPDATE
SET display_name = EXCLUDED.display_name;

INSERT INTO roles (name, description) VALUES
    ('admin', 'Full access to stores, users, and imports'),
    ('marketer', 'Can manage stores and imports'),
    ('viewer', 'Read-only store access')
ON CONFLICT (name) DO UPDATE
SET description = EXCLUDED.description;

INSERT INTO permissions (name, description) VALUES
    ('stores:read', 'Read store data'),
    ('stores:write', 'Create and update store data'),
    ('stores:delete', 'Deactivate stores'),
    ('stores:import', 'Import stores from CSV'),
    ('users:read', 'Read users'),
    ('users:write', 'Create and update users'),
    ('users:delete', 'Deactivate users')
ON CONFLICT (name) DO UPDATE
SET description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.name IN (
    'stores:read',
    'stores:write',
    'stores:delete',
    'stores:import',
    'users:read',
    'users:write',
    'users:delete'
)
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.name IN (
    'stores:read',
    'stores:write',
    'stores:delete',
    'stores:import'
)
WHERE r.name = 'marketer'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.name = 'stores:read'
WHERE r.name = 'viewer'
ON CONFLICT DO NOTHING;

INSERT INTO users (user_id, email, password_hash, role_id, status, must_change_password)
SELECT 'U001', 'admin@test.com', '$2y$12$Tg/Ts4volSJzcI.Zg3yoVuwng4sabAosWrJWFx04rchZp1NaxzL5a', id, 'active', true
FROM roles
WHERE name = 'admin'
ON CONFLICT (user_id) DO UPDATE
SET email = EXCLUDED.email,
    role_id = EXCLUDED.role_id,
    status = EXCLUDED.status,
    updated_at = now();

INSERT INTO users (user_id, email, password_hash, role_id, status, must_change_password)
SELECT 'U002', 'marketer@test.com', '$2y$12$Tg/Ts4volSJzcI.Zg3yoVuwng4sabAosWrJWFx04rchZp1NaxzL5a', id, 'active', true
FROM roles
WHERE name = 'marketer'
ON CONFLICT (user_id) DO UPDATE
SET email = EXCLUDED.email,
    role_id = EXCLUDED.role_id,
    status = EXCLUDED.status,
    updated_at = now();

INSERT INTO users (user_id, email, password_hash, role_id, status, must_change_password)
SELECT 'U003', 'viewer@test.com', '$2y$12$Tg/Ts4volSJzcI.Zg3yoVuwng4sabAosWrJWFx04rchZp1NaxzL5a', id, 'active', true
FROM roles
WHERE name = 'viewer'
ON CONFLICT (user_id) DO UPDATE
SET email = EXCLUDED.email,
    role_id = EXCLUDED.role_id,
    status = EXCLUDED.status,
    updated_at = now();

COMMIT;
