# Worker Radar Backend (FastAPI)

Backend API for authentication, worker profiles, bookings, and olive season analytics.

## Stack

- FastAPI
- SQLAlchemy ORM
- Alembic migrations
- SQLite default local DB (PostgreSQL-ready through env)
- Pytest test suite

## API Modules

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Workers
- `POST /workers` (worker role, own phone only)
- `PATCH /workers/{worker_id}` (worker role, own profile)
- `GET /workers` (worker/farmer with filters)
- `PATCH /workers/{worker_id}/availability` (worker role, own profile)
- `DELETE /workers/{worker_id}` (worker role, own profile)

### Bookings
- `POST /workers/{worker_id}/bookings` (farmer)
- `GET /bookings/mine` (farmer)
- `GET /bookings/received` (worker)
- `PATCH /bookings/{booking_id}/worker-response` (worker)
- `PATCH /bookings/{booking_id}/farmer-validation` (farmer)
- `PATCH /bookings/{booking_id}/proposal` (worker/farmer owners, non-confirmed only)
- `DELETE /bookings/{booking_id}` (worker/farmer owners, non-confirmed only)
- `GET /bookings/{booking_id}/messages`
- `POST /bookings/{booking_id}/messages`
- `GET /bookings/{booking_id}/events`

### Olive seasons (farmer)
- `GET /olive-seasons/mine`
- `POST /olive-seasons`
- `PATCH /olive-seasons/{season_id}`
- `DELETE /olive-seasons/{season_id}`

### Olive piece metrics (farmer)
- `GET /olive-piece-metrics/mine`
- `POST /olive-piece-metrics`
- `PATCH /olive-piece-metrics/{metric_id}`
- `DELETE /olive-piece-metrics/{metric_id}`

## Data Features

### Worker profile fields
- team name, phone, village/address
- coordinates
- men/women counts and rates
- overtime settings
- available dates and available status

### Olive season fields
- season year
- land piece name
- estimated/actual chonbol
- kg per land piece
- tanks 20L
- notes
- computed `kg_needed_per_tank`

### Olive piece metric fields
- season year
- piece label
- harvested kg
- tanks 20L
- notes
- computed `kg_needed_per_tank`

## Run Locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic -c alembic.ini upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Docs:
- `http://127.0.0.1:8000/docs`

## Migrations

Apply migrations:

```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini upgrade head
```

Create new migration:

```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini revision --autogenerate -m "describe change"
.\.venv\Scripts\alembic -c alembic.ini upgrade head
```

## Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

## Configuration

- Default DB: SQLite (`worker_radar.db`)
- Override with `DATABASE_URL`
- Auth env:
- `AUTH_SECRET_KEY`
- `AUTH_ALGORITHM`

CORS currently allows local Vite and local static-server origins.
