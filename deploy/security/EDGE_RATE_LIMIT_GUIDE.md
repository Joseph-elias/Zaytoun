# Edge Rate-Limit Guidance (Nginx + Cloudflare/WAF)

This guide aligns edge limits with backend defaults in `app/core/rate_limit.py`.

## Backend-aligned defaults

- Global: `240 req / 60s` per identity
- Auth login: `8 req / 60s`
- Password reset: `5 req / 300s`
- Agro general: `40 req / 60s`
- Agro AI (`/agro-copilot/chat`, `/agro-copilot/diagnose`): `10 req / 60s`

## Layering principle

Use edge limits slightly higher than app limits so:

1. Volumetric spikes are dropped early at edge.
2. Business-aware app limits still enforce final policy.

Recommended edge baselines:

- Global edge: `300 req / 60s` per IP
- Auth login edge: `12 req / 60s` per IP
- Password reset edge: `8 req / 300s` per IP
- Agro AI edge: `15 req / 60s` per IP

## Files

- Nginx example: `deploy/security/nginx-rate-limit.conf`
- Cloudflare rule examples: `deploy/security/cloudflare-rules.md`

## Important

- Keep edge and app thresholds documented together.
- When app limits change, update edge limits in the same PR.
