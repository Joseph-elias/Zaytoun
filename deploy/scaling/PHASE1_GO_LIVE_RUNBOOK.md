# Phase 1 Go-Live Validation Runbook

This runbook is the operational sequence to validate scalability for hundreds of users.

## Step 0: Preconditions

1. Staging backend is running on PostgreSQL + Redis.
2. Env values from `deploy/scaling/PHASE1_STAGING_CHECKLIST.md` are applied.
3. You have the metrics bearer token.

## Step 1: Smoke Gate

Check:
- `GET /health` = `200`
- `GET /ready` = `200`

If either fails: stop and fix infra before load testing.

## Step 2: Execute Phase 1 Automated Run

```powershell
powershell -ExecutionPolicy Bypass -File deploy/perf/run_phase1_full.ps1 `
  -BaseUrl https://your-backend.example.com `
  -MetricsBearerToken <token>
```

Expected behavior:
- users/profile auto-created if missing
- all scenarios executed
- gate evaluation at end

## Step 3: Interpret Results

### PASS

- Exit code `0`
- Final gate line:
  - `[gate] PASS: latency/error/limiter/db-pool gates passed`

Action:
- Mark Phase 1 validated for current traffic profile.
- Archive `.perf-results/staging/*.json` with date and commit SHA.

### FAIL

Use this mapping:

1. `health p95 > 150ms`
- Platform/runtime pressure.
- Action: check CPU/memory saturation, reduce noisy co-tenants, tune worker count.

2. `workers/auth/booking p95` breach
- Application + DB path under pressure.
- Action: check DB slow queries, indexes, pool size/overflow, endpoint-level cache strategy.

3. `error rate > 1%`
- Stability issue under load.
- Action: inspect 5xx logs by request ID, rollback recent changes if needed.

4. `rate limiter backend errors detected`
- Redis limiter unhealthy.
- Action: fix Redis connectivity/timeouts, verify `RATE_LIMIT_REDIS_REQUIRED=true`.

5. `DB pool reached full saturation`
- Connection bottleneck.
- Action: increase `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` carefully and check DB max connections.

## Step 4: Retest Policy

After any infra/config change:
1. rerun full Phase 1 command
2. compare p95 and failure rates with previous run
3. keep change only if metrics improve and gates pass

## Step 5: Promotion Rule

Promote to production only after:
- two consecutive PASS runs
- no severe 5xx bursts in logs
- Redis limiter backend error metric remains zero
