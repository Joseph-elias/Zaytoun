# Security Operations Runbook

This runbook is the minimum process to operate Zaytoun securely in production.

## 1) Pre-deploy security checklist

- Set `APP_ENV=production`.
- Set `AUTH_SECRET_KEY` to a strong random value (not default).
- Set explicit `CORS_ALLOWED_ORIGINS` (no `*`).
- Set `SECURITY_TRUSTED_HOSTS`.
- Enable `SECURITY_HSTS_ENABLED=true` behind HTTPS.
- Enable rate limiting:
  - `RATE_LIMIT_ENABLED=true`
  - `RATE_LIMIT_STORAGE=redis`
  - `RATE_LIMIT_REDIS_URL=<managed redis>`
  - `RATE_LIMIT_REDIS_REQUIRED=true`
- Set `RATE_LIMIT_TRUST_X_FORWARDED_FOR=true` and correct `RATE_LIMIT_TRUSTED_PROXY_CIDRS`.
- Keep `STARTUP_FAIL_FAST_VALIDATION=true`.
- Never store live secrets in tracked files.

## 2) CI security controls

Security workflow: `.github/workflows/security.yml`
Deploy gate workflow: `.github/workflows/ci-cd.yml` (`security-gates` job must pass).

Checks:
- gitleaks secret scanning
- bandit SAST
- pip-audit dependency scan
- npm audit dependency scan
- trivy config scan

Dependency update automation:
- `.github/dependabot.yml`

## 3) Observability and audit events

Primary telemetry:
- `/metrics` (optional token-guarded)
- `app.audit` logger events
- rate-limit/security events in app logs

Critical audit event families:
- auth register/login failures
- password reset requests/confirm failures
- consent re-accept
- account deletion
- agro upstream errors
- agro abuse/rate-limit blocks

## 4) Incident response (quick path)

### Suspected credential leak
1. Rotate affected credential immediately.
2. Invalidate sessions (`token_version` strategy or global key rotate when needed).
3. Review recent audit events and IP activity.
4. Block abusive IPs at edge (Cloudflare/Nginx).
5. Open incident ticket and record timeline.

### Login brute-force spike
1. Confirm rate-limit blocks in logs/metrics.
2. Tighten edge login rules temporarily.
3. Increase lockout duration if necessary.
4. Track false positives and tune thresholds.

### Agro abuse/cost spike
1. Confirm spike in `/agro-copilot/chat|diagnose`.
2. Tighten agro edge rules first.
3. Lower app agro AI limits temporarily.
4. Investigate abusive identities from audit logs.

## 5) Weekly operations cadence

- Review security CI results.
- Apply dependency update PRs.
- Check `429` trends and false positives.
- Verify backups and restoration path.
- Spot-check startup validation configs in production environment.

## 6) Quarterly controls

- Secret rotation drill.
- Dependency risk review and major upgrade plan.
- External penetration test or focused appsec review.
- Update edge WAF/rate rules based on new traffic patterns.

Reference:
- Detailed secret rotation steps: `deploy/security/SECRET_ROTATION_RUNBOOK.md`
