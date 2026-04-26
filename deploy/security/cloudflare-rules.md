# Cloudflare/WAF Rule Blueprint

Use these as managed rules in Cloudflare Rate Limiting.

## 1) Global API limit

- Expression: `http.host eq "api.example.com"`
- Scope: all paths
- Threshold: `300 requests / 60 seconds`
- Action: `Managed Challenge` (or `Block` for repeated offenders)
- Characteristics: by IP

## 2) Login brute-force guard

- Expression:
  - `http.request.uri.path eq "/auth/login"`
  - `and http.request.method eq "POST"`
- Threshold: `12 requests / 60 seconds`
- Action: `Block` for `10 minutes`

## 3) Password reset abuse guard

- Expression:
  - `(http.request.uri.path eq "/auth/password-reset/request" or http.request.uri.path eq "/auth/password-reset/confirm")`
  - `and http.request.method eq "POST"`
- Threshold: `8 requests / 300 seconds`
- Action: `Block` for `15 minutes`

## 4) Agro AI expensive endpoint guard

- Expression:
  - `(http.request.uri.path eq "/agro-copilot/chat" or http.request.uri.path eq "/agro-copilot/diagnose")`
  - `and http.request.method eq "POST"`
- Threshold: `15 requests / 60 seconds`
- Action: `Managed Challenge`

## 5) Bot management (recommended)

- Add Bot score rule on AI endpoints:
  - if bot score is low and path is agro AI -> challenge or block.

## 6) Header/host validation

- Enforce expected host only.
- Drop requests with malformed `X-Forwarded-For` at edge where possible.
