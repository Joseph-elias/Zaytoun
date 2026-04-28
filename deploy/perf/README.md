# Performance Baseline (Phase 0)

This folder defines the initial load-testing baseline for Zaytoun.

Goal: validate that current architecture can safely handle early growth and produce reproducible metrics before optimization work.

## Prerequisites

1. Install `k6`: https://k6.io/docs/get-started/installation/
2. Run backend in production-like mode (PostgreSQL + Redis limiter recommended).
3. Enable metrics on backend:
   - `METRICS_ENABLED=true`
   - `METRICS_BEARER_TOKEN=<strong-token>`

## SLO Targets (Phase 0)

- `GET /health`: p95 < `150ms`, error rate < `0.1%`
- `GET /workers` (no filters): p95 < `500ms`, error rate < `1%`
- `GET /workers` (date + location filters): p95 < `1000ms`, error rate < `1%`
- `POST /auth/login`: p95 < `700ms`, error rate < `1%` (excluding expected `401`)
- Booking flow (`create -> worker response -> farmer validation`): p95 per step < `1000ms`, error rate < `1%`

## Test Scenarios

- `health-smoke.js`: quick platform sanity check.
- `workers-list.js`: baseline worker directory read traffic.
- `auth-login.js`: login pressure and auth endpoint behavior.
- `bookings-flow.js`: end-to-end booking lifecycle pressure.

## Run Examples

```powershell
# 0) preflight (required before long load runs)
make perf-preflight

# 1) health
k6 run deploy/perf/health-smoke.js -e BASE_URL=https://your-backend.example.com

# 2) workers listing
k6 run deploy/perf/workers-list.js -e BASE_URL=https://your-backend.example.com

# 3) login pressure
k6 run deploy/perf/auth-login.js -e BASE_URL=https://your-backend.example.com -e LOGIN_PHONE=+2127000000 -e LOGIN_PASSWORD=secret123

# 4) booking flow (requires seeded users and worker)
k6 run deploy/perf/bookings-flow.js -e BASE_URL=https://your-backend.example.com -e FARMER_PHONE=+2127001000 -e FARMER_PASSWORD=secret123 -e WORKER_PHONE=+2127002000 -e WORKER_PASSWORD=secret123 -e WORKER_ID=<uuid>

# 5) staging full baseline + automatic pass/fail gates
powershell -ExecutionPolicy Bypass -File deploy/perf/run_phase0_staging.ps1 `
  -BaseUrl https://your-backend.example.com `
  -FarmerPhone +2127001000 `
  -FarmerPassword secret123 `
  -WorkerPhone +2127002000 `
  -WorkerPassword secret123 `
  -WorkerId <uuid> `
  -MetricsBearerToken <token>

# 6) phase 1 full ownership runner (auto-seed users + worker + run gates)
powershell -ExecutionPolicy Bypass -File deploy/perf/run_phase1_full.ps1 `
  -BaseUrl https://your-backend.example.com `
  -MetricsBearerToken <token>
```

Preflight ensures:
- app starts with valid runtime env
- `/health` and `/ready` are reachable
- register/login/worker-create/list seed contract still matches current API
- command exits non-zero on failure so load runs are blocked early

Staging gates enforce:
- endpoint p95 SLOs (health/workers/auth/booking)
- overall error-rate cap
- zero limiter backend errors (`worker_radar_rate_limit_backend_error_total`)
- DB pool not fully saturated (`checked_out < pool_size + overflow`)

## Result Capture Template

For each run, record:

- date/time
- git commit SHA
- scenario name
- vus/max vus and duration
- request rate (req/s)
- p50/p90/p95/p99 latency
- error rate
- backend CPU/memory
- DB CPU/connections/slow queries
- Redis CPU/memory/ops/sec

Store summaries in your release notes or operations log so regressions are visible over time.
