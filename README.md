# Worker Radar

Worker Radar is a worker-first platform connecting workers and employers in real time.

## Monorepo Structure

- `backend/` FastAPI API (auth + workers + permissions)
- `frontend/` Vite frontend (login/signup/register/my-profiles/workers)

## Quick Start

### 1) Backend

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

### 2) Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Roles

- `worker`: can create and manage only own worker profiles
- `farmer`: can browse/filter workers, no modification permissions
