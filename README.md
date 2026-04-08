# Worker Radar

Worker Radar is a monolith-first platform for agricultural operations, connecting workers, farmers, and customers through one application.

Current product scope includes:
- Worker discovery and booking workflows
- Olive season, labor, sales, usage, and inventory management
- Farmer market storefronts with customer ordering, chat, and separable ratings

## Product Areas

### 1) Auth and roles
- JWT-based auth with register/login
- Roles:
- `worker`
- `farmer`
- `customer`

### 2) Worker operations
- Workers can create and manage their own team profiles
- Farmer can search/filter workers by village, availability, date, and rate constraints
- Worker map/location support in the frontend

### 3) Booking lifecycle
- Farmer sends booking proposals
- Worker accepts/rejects
- Farmer confirms/cancels
- Proposal updates/deletes allowed before final confirmation
- Booking messages and booking event history included

### 4) Olive management
- Land pieces registry
- Olive season records with piece-level tracking
- Financial logic for pressing cost in money or oil tanks
- Labor-day inputs, sales, usage, inventory, and carry-over by year
- Insights views embedded in olive workflows

### 5) Market module (UberEats-like flow)
- Farmer creates listings (photo/logo/description/location/quantity optional)
- Customer browses store cards and enters a store detail page
- Cart checkout creates one order per cart line
- Farmer validates/rejects orders and sets pickup time
- Order chat between farmer and customer
- Store profile editor (name, banner, about, opening hours)
- Image upload from device (PNG/JPG/WEBP) for banner/logo/product photos

### 6) Separable ratings
- Store rating and product rating are independent
- Product ratings aggregate per item
- Store ratings aggregate per farmer/store
- Customer can save product rating or store rating separately

## Architecture (Current)
- **Backend:** FastAPI + SQLAlchemy + Alembic
- **Frontend:** Vite multi-page app with vanilla JS modules
- **DB (default local):** SQLite (`backend/worker_radar.db`)
- **DB target later:** PostgreSQL/Supabase via `DATABASE_URL`

Repository:
- `backend/` API, models, migrations, tests
- `frontend/` UI pages, JS modules, QA scripts

## Run Locally

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic -c alembic.ini upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Backend docs:
- `http://127.0.0.1:8000/docs`

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend app:
- `http://127.0.0.1:5173/`

## Environment

### Backend
- Config is loaded from `backend/app/core/config.py`
- `.env` is optional for local dev
- Important vars:
- `DATABASE_URL` (for Postgres/Supabase)
- `DB_FALLBACK_URL`
- `AUTH_SECRET_KEY`
- `AUTH_ALGORITHM`

Default local DB resolves to absolute path under `backend/worker_radar.db`.

### Frontend
- Use `frontend/.env.example`
- API base:
- `VITE_API_BASE_URL=http://127.0.0.1:8000`

## Database and migrations

Apply latest migrations:
```powershell
cd backend
.\.venv\Scripts\alembic -c alembic.ini upgrade head
```

Check current revision:
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

## Testing and QA

### Backend tests
```powershell
cd backend
$env:PYTHONPATH='.'
.\.venv\Scripts\pytest -q
```

Test suite is now split for maintainability:
- `backend/tests/test_auth_workers_bookings.py`
- `backend/tests/test_olive_api.py`
- `backend/tests/test_market_api.py`
- Shared helpers in `backend/tests/helpers.py`

### Frontend build
```powershell
cd frontend
npm run build
```

### Frontend automated QA scripts
Located in `frontend/scripts/`:
- `qa-full.mjs`
- `ui-feedback-smoke.mjs`
- `qa-button-bug.mjs`
- `qa-usage-history-check.mjs`

Run scripts with frontend dev server running on `127.0.0.1:5173`.

## Key pages
- `workers.html` Worker directory + filters/map
- `register.html` Worker profile creation
- `my-profiles.html` Worker-owned profiles
- `bookings.html` Booking workflows
- `olive-season.html` Olive season and budgeting workflows
- `inventory.html` Inventory management
- `insight.html` Analytics
- `market.html` Market storefronts, orders, cart, ratings

## Current maturity
- Strong MVP with full end-to-end business flows
- Good automated test coverage for backend APIs
- Browser QA smoke coverage for critical frontend flows
- CI/CD pipeline available with GitHub Actions + Render deployment workflow
- Not yet optimized for high-scale production traffic (10k concurrent users) until infra hardening phase

## Recommended next phase (when feature scope stabilizes)
- Postgres/Supabase production migration
- Redis/cache + observability stack
- Rate limiting/security hardening
- Load/performance testing and SLO tuning


## Shared frontend upload pattern
- Frontend image uploads use: `frontend/src/upload.js`
- Helper function: `uploadImageFile(file)`
- Backend upload endpoint: `POST /uploads/image`
- Uploaded files are served from: `/uploads/<filename>`
- Reuse this helper in any future module needing image upload to keep UX/API behavior consistent
