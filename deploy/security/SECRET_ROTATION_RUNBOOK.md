# Secret Rotation Runbook

This runbook defines how to rotate production secrets safely without breaking service.

## Scope

Rotate these at minimum:
- `AUTH_SECRET_KEY`
- `AGRO_COPILOT_API_KEY` / `INTERNAL_API_KEY`
- `DATABASE_URL` credentials
- `RATE_LIMIT_REDIS_URL` credentials
- `SMTP_USERNAME` / `SMTP_PASSWORD`
- any cloud/provider tokens used by CI/CD

## Rotation cadence

- High-risk secrets (API keys, CI tokens): every 30-60 days.
- App/session secrets (`AUTH_SECRET_KEY`): every 90 days or immediately after suspicion.
- DB/Redis/SMTP passwords: every 90 days or provider policy requirement.
- Immediate rotation after any suspected leak.

## Pre-rotation checklist

1. Open an incident/change ticket and define maintenance window.
2. Confirm new secret values are created in secret manager first (not in git, not in `.env` tracked files).
3. Confirm rollback secret (previous value) is still available for short rollback window.
4. Notify team that login tokens may be invalidated when rotating auth/session secrets.

## Rotation procedure (generic)

1. Create new credential in provider console.
2. Store new value in deployment secret manager.
3. Deploy environment with new secret.
4. Run smoke checks:
   - `/health` and `/ready`
   - login flow
   - agro copilot call
   - password reset email flow (if SMTP rotated)
5. Revoke old credential once new credential is confirmed.
6. Record completion timestamp and operator in ticket.

## Service-specific notes

### `AUTH_SECRET_KEY`

- Rotating this invalidates existing JWT sessions.
- Expected impact: users must log in again.
- Post-rotation check: new logins succeed, old tokens fail with `401`.

### `AGRO_COPILOT_API_KEY` / `INTERNAL_API_KEY`

- Must be updated on both services together.
- Backend and agro-copilot must match key values.
- Post-rotation check: `/agro-copilot/health` and one chat/diagnose request.

### Database / Redis credentials

- Prefer dual-user strategy:
  - create new DB/Redis user
  - switch app to new user
  - revoke old user after validation
- Post-rotation check:
  - app startup
  - migration check (`alembic current`)
  - basic read/write path

### SMTP credentials

- Post-rotation check:
  - `POST /auth/password-reset/request` for a user with email
  - verify email is delivered and code works.

## CI/CD secrets

Rotate and verify:
- Render deploy hooks
- GitHub app/personal tokens
- container registry credentials

After CI secret rotation, trigger one pipeline run and verify:
- security gates pass
- deploy hook step succeeds

## Emergency leak response

1. Rotate leaked secret immediately (do not wait for window).
2. Revoke old secret.
3. Invalidate sessions if auth secret leaked.
4. Review audit logs around leak window.
5. Add temporary edge restrictions for suspicious traffic.
6. Write incident postmortem with prevention action items.
