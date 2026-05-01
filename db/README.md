# Database Setup

This project uses PostgreSQL without PostGIS.

## Create and initialize the local database

```bash
createdb store_locator_service
psql -d store_locator_service -f db/schema.sql
psql -d store_locator_service -f db/import_stores_1000.sql
```

## Seed users

All seed users use the password `TestPassword123!` and have
`must_change_password = true`.

| Role | Email |
| --- | --- |
| Admin | `admin@test.com` |
| Marketer | `marketer@test.com` |
| Viewer | `viewer@test.com` |

## Main tables

- `stores`
- `services`
- `store_services`
- `users`
- `roles`
- `permissions`
- `role_permissions`
- `refresh_tokens`
- `geocode_cache`
