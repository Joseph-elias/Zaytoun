# Scalability & Infrastructure Roadmap

This roadmap is focused on moving from local stability to reliable operation with hundreds of active users.

## Phase 1: Stabilize Runtime (now)

Goals:
- No hidden startup/runtime misconfiguration in performance runs.
- Distinguish real capacity issues from bad test inputs.

Actions:
- Enforce `perf-preflight` before any load run.
- Use `perf-phase0-safe` (preflight + load).
- Keep API seed payloads aligned with schemas.
- Keep readiness strict (`/ready`) for DB + limiter backend.

Exit criteria:
- `perf-preflight` passes consistently.
- No unexpected 422s during load seeding.
- No startup crashes under valid env.

## Phase 2: Production-Like Baseline

Goals:
- Stop using SQLite/memory limiter for capacity signal.
- Measure with PostgreSQL + Redis, same as production architecture.

Actions:
- Run baseline on staging with:
  - managed PostgreSQL
  - Redis rate-limit backend
  - production-like worker count (`WEB_CONCURRENCY`)
- Capture p50/p95/p99 latency and 429 ratio by endpoint.
- Track DB connections and slow queries during tests.

Exit criteria:
- p95 within SLO for health/workers/auth/booking.
- No 5xx spikes at expected load.
- Redis/DB saturation points documented.

## Phase 3: Throughput Hardening

Goals:
- Increase sustainable throughput while keeping protections.

Actions:
- Tune global authenticated limiter separately from anonymous limiter.
- Add/verify DB indexes for hottest worker search filters.
- Tune Gunicorn/Uvicorn worker count by CPU core and memory.
- Introduce endpoint-level cache strategy for high-read lists.

Exit criteria:
- Higher req/s at same latency target.
- 429 mostly on abuse-shaped traffic, not normal user traffic.

## Phase 4: Observability & Operations

Goals:
- Fast incident diagnosis and safe rollback.

Actions:
- Centralize logs with request IDs.
- Alert on:
  - 5xx rate
  - latency p95 drift
  - DB connection exhaustion
  - Redis backend errors
- Keep runbooks updated for:
  - limiter overload
  - DB slowdown
  - dependency outage.

Exit criteria:
- On failure, root cause identified within minutes, not hours.
- Rollback/recovery drill performed successfully.

## Phase 5: Scale-Out Architecture

Goals:
- Handle regional growth and burst traffic safely.

Actions:
- Add read replicas when read pressure dominates.
- Move heavy async tasks to worker queues.
- Introduce API gateway/WAF edge controls per region.
- Split services only when operational metrics prove bottlenecks.

Exit criteria:
- Horizontal scaling plan tested with canary rollout.
- Clear service ownership and SLO per domain.

## Execution Rule

Always run:

1. `make perf-preflight`
2. `make perf-phase0-safe`

If preflight fails, treat it as config/contract issue, not capacity issue.
