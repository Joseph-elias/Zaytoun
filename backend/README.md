# Worker Radar Backend

FastAPI backend for Worker Radar, covering auth, workers, bookings, olive operations, and market flows.

## Stack
- FastAPI
- SQLAlchemy ORM
- Alembic
- SQLite local default (`worker_radar.db`)
- PostgreSQL/Supabase-ready through `DATABASE_URL`
- Pytest

## Core API Areas

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/me/profile`
- `PATCH /auth/me/password`
- `POST /auth/password-reset/request`
- `POST /auth/password-reset/confirm`

### Workers
- `POST /workers`
- `PATCH /workers/{worker_id}`
- `GET /workers`
- `PATCH /workers/{worker_id}/availability`
- `DELETE /workers/{worker_id}`

### Bookings
- `POST /workers/{worker_id}/bookings`
- `GET /bookings/mine`
- `GET /bookings/received`
- `PATCH /bookings/{booking_id}/worker-response`
- `PATCH /bookings/{booking_id}/farmer-validation`
- `PATCH /bookings/{booking_id}/proposal`
- `DELETE /bookings/{booking_id}`
- `GET /bookings/{booking_id}/messages`
- `POST /bookings/{booking_id}/messages`
- `GET /bookings/{booking_id}/events`

### Olive domain
- `olive-seasons` CRUD + oil tank price endpoints
- `olive-land-pieces` registry
- `olive-labor-days`
- `olive-sales`
- `olive-usages`
- `olive-inventory-items`
- `olive-piece-metrics`

### Market domain
- `market/items` CRUD (farmer)
- `market/orders` create/list/validate
- order chat endpoints
- customer review endpoint with **separable product/store ratings**
- store profile endpoints

### Agro Copilot integration (farmer-only)
- `GET /agro-copilot/health`
- `GET /agro-copilot/knowledge/sources`
- `POST /agro-copilot/chat`
- `POST /agro-copilot/diagnose`

## Local Run
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic -c alembic.ini upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open docs:
- `http://127.0.0.1:8000/docs`

## Migrations

Upgrade:
```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini upgrade head
```

Current revision:
```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini current
```

Create migration:
```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini revision --autogenerate -m "describe_change"
.\.venv\Scripts\alembic -c alembic.ini upgrade head
```

## Tests

```powershell
cd backend
$env:PYTHONPATH='.'
.\.venv\Scripts\pytest -q
```

Test modules:
- `tests/test_auth_workers_bookings.py`
- `tests/test_olive_api.py`
- `tests/test_market_api.py`
- `tests/test_agro_copilot_api.py`
- shared helpers in `tests/helpers.py`

## Configuration

Loaded from `app/core/config.py`.

Important env vars:
- `DATABASE_URL`
- `DB_FALLBACK_URL`
- `AUTH_SECRET_KEY`
- `AUTH_ALGORITHM`
- `AUTH_CONSENT_VERSION`
- `AUTH_PASSWORD_RESET_DEV_MODE`
- `AUTH_PASSWORD_RESET_CODE_TTL_MINUTES`
- `AUTH_PASSWORD_RESET_MAX_ATTEMPTS`
- `AUTH_PASSWORD_RESET_EMAIL_ENABLED`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`
- `SMTP_USE_SSL`
- `AGRO_COPILOT_API_BASE_URL`
- `AGRO_COPILOT_API_KEY`
- `AGRO_COPILOT_TIMEOUT_SECONDS`
- `AGRO_COPILOT_MAX_RETRIES`
- `AGRO_COPILOT_RETRY_BACKOFF_MS`

Auth payload requirements:
- `POST /auth/register` requires:
  - `terms_accepted=true`
  - `data_consent_accepted=true`
  - `consent_version` (for example `2026-04-13`)
- `POST /auth/login` requires:
  - `legal_acknowledged=true`
- Re-consent flow:
  - If a user signed with an older consent version, `/auth/login` returns
    `consent_reaccept_required=true` and `required_consent_version`.
  - Use `PATCH /auth/consent` with:
    - `legal_acknowledged=true`
    - `terms_accepted=true`
    - `data_consent_accepted=true`
    - `consent_version=<required_consent_version>`
- Password reset flow:
  - `POST /auth/password-reset/request` with `phone`
    - Always returns a generic success message (prevents account enumeration).
    - In development only (`AUTH_PASSWORD_RESET_DEV_MODE=true`), returns `debug_reset_code`.
  - `POST /auth/password-reset/confirm` with:
    - `phone`
    - `reset_code`
    - `new_password`
  - Reset codes expire based on `AUTH_PASSWORD_RESET_CODE_TTL_MINUTES` and are blocked after `AUTH_PASSWORD_RESET_MAX_ATTEMPTS` invalid tries.
  - When `AUTH_PASSWORD_RESET_EMAIL_ENABLED=true`, reset codes are sent by SMTP to the user's registered `email`.
  - Keep `AUTH_PASSWORD_RESET_DEV_MODE=false` in production.
- Enterprise security controls:
  - Changing `phone` or `email` through `PATCH /auth/me/profile` requires `current_password`.
  - Any password update (`PATCH /auth/me/password` or reset confirm) invalidates previous sessions immediately.

## Security Highlights

This backend includes production-style auth hardening patterns with endpoint-level guarantees:

- **Consent gate before protected data**
  - `POST /auth/login` can return:
    - `consent_reaccept_required=true`
    - `required_consent_version=<current_version>`
  - Protected routes then return `403` until `PATCH /auth/consent` is completed.

- **Sensitive profile changes require re-auth**
  - `PATCH /auth/me/profile` accepts:
    - `full_name`
    - `phone`
    - `email`
    - `current_password` (required when changing `phone` or `email`)
  - This prevents account takeover via stolen active sessions.

- **Password rotation revokes active sessions**
  - `PATCH /auth/me/password` requires `current_password` + `new_password`.
  - `POST /auth/password-reset/confirm` resets password with one-time code.
  - Both paths rotate auth token version so old JWTs are rejected with `401`.

- **Enumeration-resistant recovery**
  - `POST /auth/password-reset/request` always returns a generic success message,
    even when the account does not exist.
  - Reset verification is protected with expiry and max-attempt limits.

### Example: Sensitive profile update (re-auth)
```http
PATCH /auth/me/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "Worker Updated",
  "phone": "+2127993999",
  "email": "worker.updated@example.com",
  "current_password": "secret123"
}
```

### Example: Password change and automatic session revocation
```http
PATCH /auth/me/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "secret123",
  "new_password": "new-secret-123"
}
```
After success, previously issued tokens are invalid and protected routes return `401` until re-login.

Default local DB resolves to an absolute file path under `backend/worker_radar.db`.



