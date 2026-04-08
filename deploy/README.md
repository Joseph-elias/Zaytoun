# CI/CD Deployment Setup (Render)

This repo now deploys to Render.

## Pipeline behavior

1. On PR and push to `main`, GitHub Actions runs:
   - backend tests (`pytest`)
   - frontend build (`npm run build`)
   - Docker image build validation for backend/frontend (no push)
2. On push to `main`, GitHub Actions triggers Render deploy hooks.

Workflow file:
- `.github/workflows/ci-cd.yml`

## Render service model

`render.yaml` defines two services:

- `zaytoun-backend` (Web Service, Python, `backend/`)
- `zaytoun-frontend` (Static Site, Node build, `frontend/`)

## Setup steps

1. In Render, create services from this repo (Blueprint recommended).
2. Ensure backend env vars are set in Render:
   - `DATABASE_URL`
   - `DB_FALLBACK_URL` (can be same as `DATABASE_URL`)
   - `AUTH_SECRET_KEY`
   - `AUTH_ALGORITHM` (optional, default `HS256`)
3. Set frontend env var in Render:
   - `VITE_API_BASE_URL` = your backend public URL (for example `https://zaytoun-backend.onrender.com`)
4. In Render, copy deploy hook URLs:
   - backend deploy hook
   - frontend deploy hook
5. In GitHub repository secrets, set:
   - `RENDER_BACKEND_DEPLOY_HOOK`
   - `RENDER_FRONTEND_DEPLOY_HOOK`

## Notes

- Backend start command runs migrations before startup.
- If deploy hook secrets are missing, CI still runs tests/build, and deploy steps are skipped.
- Backend runtime tuning envs are supported in Docker deployments: `RUN_MIGRATIONS`, `WEB_CONCURRENCY`, `WEB_TIMEOUT`, `WEB_GRACEFUL_TIMEOUT`, `WEB_KEEPALIVE`.
