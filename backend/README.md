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
- shared helpers in `tests/helpers.py`

## Configuration

Loaded from `app/core/config.py`.

Important env vars:
- `DATABASE_URL`
- `DB_FALLBACK_URL`
- `AUTH_SECRET_KEY`
- `AUTH_ALGORITHM`

Default local DB resolves to an absolute file path under `backend/worker_radar.db`.
