# Phase 1 Staging Checklist (PostgreSQL + Redis)

Use this checklist before running Phase 1 load validation.

## 1) Runtime Topology

- Backend deployed with `APP_ENV=staging` (or `production` if this is pre-prod).
- Database is PostgreSQL (not SQLite).
- Rate limiter storage is Redis (not memory).

## 2) Required Environment Variables

Set these on backend service:

- `APP_ENV=staging`
- `DATABASE_URL=<postgresql+psycopg://...>`
- `DB_FALLBACK_URL=<same as DATABASE_URL>`
- `DB_POOL_SIZE=20`
- `DB_MAX_OVERFLOW=40`
- `DB_POOL_TIMEOUT_SECONDS=30`
- `DB_POOL_RECYCLE_SECONDS=1800`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_STORAGE=redis`
- `RATE_LIMIT_REDIS_URL=<redis://...>`
- `RATE_LIMIT_REDIS_REQUIRED=true`
- `RATE_LIMIT_TRUST_X_FORWARDED_FOR=true`
- `RATE_LIMIT_GLOBAL_REQUESTS=300`
- `RATE_LIMIT_GLOBAL_WINDOW_SECONDS=60`
- `RATE_LIMIT_GLOBAL_AUTHENTICATED_REQUESTS=1800`
- `RATE_LIMIT_GLOBAL_AUTHENTICATED_WINDOW_SECONDS=60`
- `RATE_LIMIT_AUTH_LOGIN_REQUESTS=20`
- `RATE_LIMIT_AUTH_LOGIN_WINDOW_SECONDS=60`
- `METRICS_ENABLED=true`
- `METRICS_REQUIRE_PROMETHEUS_CLIENT=true`
- `METRICS_PATH=/metrics`
- `METRICS_BEARER_TOKEN=<strong token>`

## 3) Readiness and Security

- `/health` returns `200`.
- `/ready` returns `200` and confirms DB + limiter backend healthy.
- `STARTUP_FAIL_FAST_VALIDATION=true`.

## 4) Phase 1 Execution

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/perf/run_phase1_full.ps1 `
  -BaseUrl https://your-backend.example.com `
  -MetricsBearerToken <token>
```

This command will:
- seed/validate farmer and worker users
- ensure worker profile exists
- run health/workers/auth/booking load scenarios
- enforce automatic pass/fail gates

## 5) Go/No-Go Criteria

Go only if:
- script exits code `0`
- gate output contains:
  - `[gate] PASS: latency/error/limiter/db-pool gates passed`

No-Go if any of:
- p95 SLO breach
- request error rate > 1%
- limiter backend errors (`worker_radar_rate_limit_backend_error_total > 0`)
- DB pool saturation (`checked_out >= pool_size + overflow`)
