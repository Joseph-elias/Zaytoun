# Worker Radar Frontend

Vite multi-page frontend for Worker Radar.

## Tech
- Vite
- Vanilla JS modules
- Multi-page HTML app
- Playwright-based QA scripts

## Main Pages
- `workers.html`: worker discovery and filtering
- `register.html`: worker profile creation
- `my-profiles.html`: worker profile management
- `bookings.html`: booking workflows + chat/events
- `olive-season.html`: season entry, budgeting, usage, embedded insights
- `inventory.html`: inventory management
- `insight.html`: analytics page (supports `?embedded=1`)
- `market.html`: market storefronts, store profile, listings, cart/orders/ratings

## Market UX Highlights
- Store cards and store detail experience
- Farmer listing builder with image/logo/description/quantity handling
- Customer cart and checkout flow
- Farmer order validation/rejection and pickup scheduling
- Order chat
- Separable ratings:
- Product rating per listing/product
- Store rating per market/store

## Shared Upload Pattern
- Use `frontend/src/upload.js` and `uploadImageFile(file)` for all image uploads.
- Current backend upload endpoint: `POST /uploads/image`.
- Accepted formats: PNG, JPG/JPEG, WEBP.
- New modules should use file inputs (`type="file"`) and upload first, then persist returned URL.

## Role Routing
- Worker home: `register.html`
- Farmer home: `workers.html`
- Customer home: `market.html`
- If backend requires policy re-acceptance, authenticated users are redirected to `consent.html`.

Unauthenticated users are redirected to `index.html`.

## Local Run

Start backend first (`http://127.0.0.1:8000`), then:

```powershell
cd frontend
npm install
npm run dev
```

Open:
- `http://127.0.0.1:5173/`

## Build

```powershell
cd frontend
npm run build
npm run preview
```

## Environment

Set API base URL:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use `frontend/.env.example` as template.

## QA Scripts

Under `frontend/scripts/`:
- `qa-full.mjs`
- `ui-feedback-smoke.mjs`
- `qa-button-bug.mjs`
- `qa-usage-history-check.mjs`

Run them against a live dev server on `127.0.0.1:5173`.

