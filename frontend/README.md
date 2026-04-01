# Worker Radar Frontend (Vite Multi-Page)

Frontend for worker and farmer workflows using vanilla JS modules and role-based navigation.

## Pages

- `index.html`: landing/entry
- `login.html`: login
- `signup.html`: account registration
- `workers.html`: worker directory + map + filters
- `register.html`: worker profile creation
- `my-profiles.html`: worker-owned profile management
- `bookings.html`: booking management + chat + timeline
- `olive-season.html`: season entry/history + embedded insights
- `insight.html`: full analytics page (also embeddable)
- `settings.html`: account settings

## Current UX Behavior

### Role routing
- Worker home: `register.html`
- Farmer home: `workers.html`
- Unauthenticated access redirects to `login.html`

### Worker side
- Manage own profiles only
- Update availability and profile details
- Receive/respond to booking proposals

### Farmer side
- Browse workers and use geographic/rate/date filters
- Create and negotiate bookings
- Track olive season records
- Open Insights inside Olive Season page via toggle

### Olive Season page specifics
- Records are editable and deletable.
- Shows computed `kg needed per tank`.
- Shows Draft badge when record is incomplete.
- Shows live progress counter: `Drafts: X / Y`.
- Insights section is hidden by default and loaded on demand.

### Insights page specifics
- Filter bar (year range, selected pieces, metric type)
- KPI cards, trend charts, comparison tables
- Piece diagnostics (trend slope, volatility, quality)
- Supports embedded mode via `?embedded=1`

## API Target

Set frontend API base via env var:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use `.env.example` as template.

## Run Locally

Start backend first:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Start frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:
- `http://127.0.0.1:5173/`

## Build

```powershell
cd frontend
npm run build
npm run preview
```

Note: in restricted sandboxes, Vite build may fail with `esbuild spawn EPERM` even when code is valid.
