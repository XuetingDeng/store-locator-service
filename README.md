# Store Locator Service

Production-style Store Locator API for public store search and authenticated internal store management.

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL 16+ without PostGIS
- geopy for distance calculation
- PyJWT for JWT access tokens
- bcrypt for password hashing
- Python built-in `csv` module for CSV import
- In-memory rate limiting for public search
- Database-backed geocoding cache

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
createdb store_locator_service
psql -d store_locator_service -f db/schema.sql
psql -d store_locator_service -f db/import_stores_1000.sql
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload
```

Default local database URL:

```text
postgresql+psycopg://dengxueting@localhost:5432/store_locator_service
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET /health
```

## Seed Users

All seed users use password `TestPassword123!`.

| Role | Email |
| --- | --- |
| Admin | `admin@test.com` |
| Marketer | `marketer@test.com` |
| Viewer | `viewer@test.com` |

## Authentication Flow

1. `POST /api/auth/login` with email/password.
2. Use the returned access token as `Authorization: Bearer <token>`.
3. Use `POST /api/auth/refresh` with the refresh token when the access token expires.
4. Use `POST /api/auth/logout` to revoke the refresh token.

Access tokens expire after 15 minutes. Refresh tokens expire after 7 days and are stored hashed in the database for revocation.

## API Summary

Auth:

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Public search:

- `POST /api/stores/search`

Admin stores:

- `POST /api/admin/stores`
- `GET /api/admin/stores`
- `GET /api/admin/stores/{store_id}`
- `PATCH /api/admin/stores/{store_id}`
- `DELETE /api/admin/stores/{store_id}`
- `POST /api/admin/stores/import`

Admin users:

- `POST /api/admin/users`
- `GET /api/admin/users`
- `PUT /api/admin/users/{user_id}`
- `DELETE /api/admin/users/{user_id}`

## Public Store Search

Search accepts exactly one of:

```json
{"latitude": "28.581300", "longitude": "-81.386200"}
```

```json
{"postal_code": "32801"}
```

```json
{"address": "100 Cambridge St, Boston, MA"}
```

Query filters:

- `radius_miles`, default `10`, max `100`
- `services`, repeatable query param, AND logic
- `store_types`, repeatable query param, OR logic
- `open_now`, optional boolean

Example:

```text
POST /api/stores/search?radius_miles=25&services=pickup&store_types=outlet
```

## Distance Calculation

The search implementation uses the required two-step approach:

1. Calculate a bounding box around the search coordinates.
2. Use SQL to pre-filter active stores within that box.
3. Use `geopy.distance.geodesic` to calculate exact distance in miles.
4. Filter by radius and sort nearest first.

## CSV Import

Endpoint:

```text
POST /api/admin/stores/import
```

Use `multipart/form-data` with a `file` field containing a CSV file. The import:

- Requires the exact header order from the project description
- Validates every row
- Creates new stores and updates existing stores by `store_id`
- Uses a transaction for store writes
- Returns created/updated/failed counts and row-level errors

## RBAC

Admin:

- Full store and user management
- CSV import

Marketer:

- Store management
- CSV import
- No user management

Viewer:

- Read-only store access

## Tests

Run:

```bash
.venv/bin/pytest
```

Coverage report:

```text
htmlcov/index.html
```

Current verified coverage: 89%.

Smoke scripts are also available:

```bash
.venv/bin/python scripts/verify_auth_flow.py
.venv/bin/python scripts/verify_store_admin_flow.py
.venv/bin/python scripts/verify_user_admin_flow.py
.venv/bin/python scripts/verify_public_search_flow.py
```

## Deployment

The app is ready for platforms like Render, Railway, Heroku, or similar.

Required environment variables:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB_NAME
JWT_SECRET_KEY=<strong-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://your-frontend.example.com
```

Production start command:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

Deployment checklist:

- Provision PostgreSQL
- Run `db/schema.sql`
- Run `db/import_stores_1000.sql`
- Configure environment variables
- Start the app with the production command
- Verify `/health`
- Verify `/docs`

No live cloud URL is included because deployment requires access to the target platform account.

## Database Schema

Core tables:

- `stores`
- `services`
- `store_services`
- `users`
- `roles`
- `permissions`
- `role_permissions`
- `refresh_tokens`
- `geocode_cache`

Schema scripts live in [db/schema.sql](/Users/dengxueting/store-locator-service/db/schema.sql).
