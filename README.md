# Worker Radar

Worker Radar is a worker-farmer coordination platform for agricultural labor.

## What The App Does Today

### Authentication and roles
- Account registration and login with JWT auth.
- Two roles:
- `worker`: can create/manage only their own worker profiles.
- `farmer`: can discover workers, create bookings, and manage olive season analytics.

### Worker management
- Workers can create multiple profiles (teams).
- Worker profiles include:
- identity and contact info
- village and optional full address
- map coordinates (lat/lon)
- men/women counts and separate rates
- overtime settings
- availability dates and availability status
- Workers can modify or delete their own profiles.
- Farmers can browse/filter/search worker directory but cannot modify worker profiles.

### Worker discovery and map
- Directory filtering by availability, village, date, rates, and location distance.
- Worker map with location pins and lightweight hover info.
- Expanded worker details shown outside map selection panel.

### Booking lifecycle (worker-farmer)
- Farmers create booking proposals for worker teams.
- Worker can accept/reject.
- Farmer can confirm/cancel after worker response.
- Non-confirmed proposals can be modified/deleted by corresponding owners.
- Confirmed bookings are protected from modification/deletion.
- Booking timeline events are tracked.
- Booking chat/messages are available between worker and farmer.

### Olive season tracking (farmer)
- Farmers can create/update/delete season records.
- Season record includes:
- season year
- land piece name
- estimated and actual chonbol
- kg per land piece
- tanks produced (20L)
- notes
- Calculated `kg needed per tank` shown from:
- `kg_per_land_piece / tanks_20l` (fallback to `actual_chonbol / tanks_20l` when needed)
- Incomplete records are marked with a Draft badge and missing fields list.
- History header includes live progress counter: `Drafts: X / Y`.

### Insights and analytics
- Dedicated insights page exists (`insight.html`) and is embedded inside Olive Season view.
- Insights panel in Olive Season is hidden by default and toggled by button.
- Analytics include:
- KPI summary cards
- year-over-year trend chart and table
- piece comparison chart and table
- diagnostics (trend slope, volatility, data quality)
- interactive filters (year range, selected pieces, metric type)

## Monorepo Structure

- `backend/`: FastAPI API + SQLAlchemy + Alembic + tests
- `frontend/`: Vite multi-page frontend (HTML + vanilla JS)

## Quick Start

### 1) Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic -c alembic.ini upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Backend docs:
- `http://127.0.0.1:8000/docs`

### 2) Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:
- `http://127.0.0.1:5173/`

## Testing

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

## Environment

Backend supports SQLite by default (`worker_radar.db`) and can be pointed to PostgreSQL via `DATABASE_URL`.

## Current Product Notes

- Mobile-first UI with role-based tab navigation.
- Farmer insights are intentionally available from Olive Season page (toggle), not always visible in top tabs.
- Project remains monolith-first to keep shipping speed high.
