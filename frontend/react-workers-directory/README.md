# Zaytoun Workers Directory (Next.js + Tailwind)

This folder contains a production-ready page implementation for the Workers Directory UI.

## Structure

- `app/page.tsx` - main page
- `app/globals.css` - base styles and glass utilities
- `components/*` - reusable UI components
- `data/mock.ts` - mock data

## Quick Start

1. Create a Next.js app (or use an existing one):
```bash
npx create-next-app@latest zaytoun-ui --typescript --tailwind --app
```
2. Copy this folder's `app`, `components`, and `data` into the Next.js project root.
3. Copy assets into `public/`:
   - `frontend/assets/workers-directory-bg.png` -> `public/workers-directory-bg.png`
   - `frontend/assets/zaytoun-logo.png` -> `public/zaytoun-logo.png`
4. Install map dependencies:
```bash
npm i leaflet react-leaflet
```
5. Run:
```bash
npm run dev
```

## Notes

- `MapSection` is client-only and uses OpenStreetMap tiles.
- The UI is responsive: desktop split layout, tablet stacked map, mobile scrollable pills.
