# Worker Radar Backend (MVP)

This service is API-only (FastAPI).

## Auth APIs

- `POST /auth/register` create account with role `worker` or `farmer`
- `POST /auth/login` get bearer token

## Worker APIs (protected)

- `POST /workers` (worker role only + own phone only)
- `GET /workers` (worker or farmer)
  - workers only see their own profiles
  - farmers can see all profiles
- `PATCH /workers/{id}/availability` (worker role only + own profile only)

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs:

- `http://127.0.0.1:8000/docs`

## Frontend

Frontend is separate in `../frontend` and uses Vite.

```bash
cd frontend
npm install
npm run dev
```

CORS is enabled for:

- `http://127.0.0.1:5173`
- `http://localhost:5173`

## Database

Default: SQLite (`worker_radar.db`) for quick local startup.

Supabase wiring is prepared in config, but inactive until env vars are set.

Option 1 (direct):

```bash
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname?sslmode=require
```

Option 2 (built from separate Supabase vars):

```bash
SUPABASE_DB_HOST=...
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=...
SUPABASE_DB_USER=...
SUPABASE_DB_PASSWORD=...
SUPABASE_DB_SSLMODE=require
```

## Auth config

```bash
AUTH_SECRET_KEY=change-me-in-production
AUTH_ALGORITHM=HS256
```

If you already created `worker_radar.db` with older fields, delete it once and restart the API so the new schema is created.
