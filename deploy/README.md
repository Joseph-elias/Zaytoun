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
- Deploy is blocked unless CI security gates pass (gitleaks, pip-audit, npm audit, trivy config).
- In GitHub branch protection for `main`, require status checks from CI/CD (including `Security Gates`) before merge.

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
    - Optional MFA tuning: `AUTH_MFA_TOTP_ISSUER`, `AUTH_MFA_TOTP_DIGITS`, `AUTH_MFA_TOTP_PERIOD_SECONDS`, `AUTH_MFA_TOTP_VALID_WINDOW`
    - `APP_ENV=production`
   - `CORS_ALLOWED_ORIGINS` (explicit comma-separated allowlist)
    - `SECURITY_TRUSTED_HOSTS` (comma-separated)
    - `SECURITY_CONTENT_SECURITY_POLICY_REPORT_ONLY` (`true` during CSP rollout, then `false` to enforce)
    - Either `SECURITY_CONTENT_SECURITY_POLICY_REPORT_URI` or `SECURITY_CSP_REPORT_ENDPOINT_ENABLED=true`
    - `AGRO_COPILOT_API_BASE_URL` (public URL of `zaytoun-agro-copilot`)
    - `AGRO_COPILOT_API_KEY` (must match agro `INTERNAL_API_KEY`)
   - Optional: `AGRO_COPILOT_TIMEOUT_SECONDS`, `AGRO_COPILOT_MAX_RETRIES`, `AGRO_COPILOT_RETRY_BACKOFF_MS`
   - Recommended: `RATE_LIMIT_STORAGE=redis`, `RATE_LIMIT_REDIS_URL`, `RATE_LIMIT_REDIS_REQUIRED=true`
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
- In production, backend startup validation can fail fast on insecure config (`STARTUP_FAIL_FAST_VALIDATION=true`).

## Performance Baseline (Phase 0)

- Load testing scenarios and SLO baseline are in `deploy/perf/`.
- Start with `deploy/perf/README.md` and run k6 scenarios against staging before production tuning.
- Enable metrics first: `METRICS_ENABLED=true` and set `METRICS_BEARER_TOKEN`.
- Always run `make perf-preflight` before long load runs.
- Use `make perf-phase0-safe` to automatically block load tests when preflight fails.

## Scalability Roadmap

- See `deploy/scaling/ROADMAP.md` for phased infrastructure scaling plan and exit criteria.
- Phase 1 staging checklist: `deploy/scaling/PHASE1_STAGING_CHECKLIST.md`
- Phase 1 go-live runbook: `deploy/scaling/PHASE1_GO_LIVE_RUNBOOK.md`

## Edge Security Artifacts

- `deploy/security/EDGE_RATE_LIMIT_GUIDE.md`
- `deploy/security/nginx-rate-limit.conf`
- `deploy/security/cloudflare-rules.md`
- `deploy/security/SECURITY_OPERATIONS_RUNBOOK.md`
- `deploy/security/SECRET_ROTATION_RUNBOOK.md`
