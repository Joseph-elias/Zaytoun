# CI/CD Deployment Setup (Render)

This repo deploys to Render with 3 services:

- `zaytoun-agro-copilot` (Web Service, Python, `Agro-copilot/`)
- `zaytoun-backend` (Web Service, Python, `backend/`)
- `zaytoun-frontend` (Static Site, Node build, `frontend/`)

## Pipeline behavior

1. On PR and push to `main`, GitHub Actions runs:
   - backend tests (`pytest`)
   - frontend build (`npm run build`)
   - Docker image build validation for backend/frontend/agro-copilot (no push)
2. On push to `main`, GitHub Actions triggers Render deploy hooks.

Workflow file:
- `.github/workflows/ci-cd.yml`

## Setup steps

1. In Render, create services from this repo (Blueprint recommended).
2. Set agro-copilot env vars:
   - `OPENAI_API_KEY`
   - `INTERNAL_API_KEY` (must match backend `AGRO_COPILOT_API_KEY`)
   - Optional: `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_TIMEOUT_SECONDS`
3. Set backend env vars:
   - `DATABASE_URL`
   - `DB_FALLBACK_URL` (can be same as `DATABASE_URL`)
   - `AUTH_SECRET_KEY`
   - `AGRO_COPILOT_API_BASE_URL` (public URL of `zaytoun-agro-copilot`)
   - `AGRO_COPILOT_API_KEY` (must match agro `INTERNAL_API_KEY`)
   - Optional: `AGRO_COPILOT_TIMEOUT_SECONDS`, `AGRO_COPILOT_MAX_RETRIES`, `AGRO_COPILOT_RETRY_BACKOFF_MS`
4. Set frontend env var:
   - `VITE_API_BASE_URL` = backend public URL (for example `https://zaytoun-backend.onrender.com`)
5. In Render, copy deploy hook URLs for all services.
6. In GitHub repository secrets, set:
   - `RENDER_AGRO_COPILOT_DEPLOY_HOOK`
   - `RENDER_BACKEND_DEPLOY_HOOK`
   - `RENDER_FRONTEND_DEPLOY_HOOK`

## Notes

- Backend proxies farmer-only requests to agro-copilot via `/agro-copilot/*`.
- Agro-copilot `/api/v1/*` endpoints can be protected with `INTERNAL_API_KEY`.
- Backend retries transient upstream errors for GET requests only.
