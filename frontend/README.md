# Worker Radar Frontend (Vite)

Standalone frontend built with Vite (multi-page HTML + JS modules).

## Pages

- `login.html`: login only
- `signup.html`: create account (worker or farmer)
- `register.html`: worker-only worker profile creation
- `my-profiles.html`: worker-owned profiles only
- `workers.html`: worker/farmer directory browsing (availability toggle only for worker role)

## Behavior

- Login redirects by role:
  - worker -> `register.html`
  - farmer -> `workers.html`
- Unauthenticated users are redirected to `login.html`

## API target

Configured via env var:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Create `.env` from `.env.example` if needed.

## Run

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
- `http://127.0.0.1:5173/login.html`
- `http://127.0.0.1:5173/signup.html`
- `http://127.0.0.1:5173/register.html`
- `http://127.0.0.1:5173/my-profiles.html`
- `http://127.0.0.1:5173/workers.html`

## Build

```powershell
cd frontend
npm run build
npm run preview
```
