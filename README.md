# Zaytoun Platform

Zaytoun is a production-minded agricultural platform that unifies workforce operations, olive farm management, digital commerce, and AI-assisted disease support in one system.

## Product Preview

![Zaytoun Landing Page](assets/landing-marketing.jpeg)

## My Why

This platform was built from my love for my land, shaped by my real experience as a farmer, and driven by the urgent need for digitization in agriculture. I created Zaytoun to bring practical, modern tools to farmers and agricultural workers, so daily operations become easier, decisions become smarter, and rural work gains the efficiency and visibility it deserves.

This repository demonstrates a complex real-world integration challenge:
- multi-role business workflows (`worker`, `farmer`, `customer`)
- transactional operations (bookings, market orders, ratings, messaging)
- farm-domain planning and finance tracking (olive seasons, labor, inventory, sales)
- secure AI microservice integration (farmer-only Agro Copilot with backend proxy and service-to-service key)

## Why This Project Matters

Most projects solve one isolated problem. Zaytoun solves an ecosystem problem.

It handles:
- labor supply and demand matching
- farm-season planning and operational accounting
- marketplace conversion from production to customer orders
- AI-assisted agronomy support for field decisions

The platform is intentionally built to be useful now while already prepared for scale-up and deployment hardening.

## System Highlights

### 1) Role-driven platform design
- JWT auth and role-based access controls
- strict ownership rules for worker/farmer/customer data
- protected farmer-only AI endpoints via backend authorization

### 2) End-to-end operational depth
- worker profiles, filtering, map/location-aware discovery
- booking lifecycle with status transitions, negotiation, and timeline events
- olive season management with labor, sales, usage, inventory carry-over, and insights

### 3) Commerce workflows
- farmer storefront management
- customer browsing, cart and ordering
- farmer validation, pickup flow, order messaging
- separable product and store ratings

### 4) AI integration done professionally
- Agro Copilot integrated as a dedicated service
- backend proxy layer (`/agro-copilot/*`) to enforce business access policy
- internal service key support (`INTERNAL_API_KEY` / `AGRO_COPILOT_API_KEY`)
- deploy wiring for Render + Docker Compose + CI validation

## Current Stage

**Stage: Advanced MVP / Pre-Production Integration**

What is already strong:
- complete core feature loops across labor, farm operations, market, and AI support
- test coverage on key backend business flows
- CI/CD pipeline and deployment blueprints
- production-style auth boundaries and service separation

What is next for full production scale:
- observability (metrics, tracing, dashboards)
- rate limiting and abuse protection policies
- load testing and performance tuning under concurrency
- stronger reliability controls (queueing/circuit breaker where needed)

## Architecture

- **Backend:** FastAPI + SQLAlchemy + Alembic
- **Frontend:** Vite multi-page app (vanilla JS modules)
- **Database (local):** SQLite
- **Production target:** PostgreSQL/Supabase
- **AI Service:** Agro Copilot (FastAPI), proxied by backend
- **Deployment:** Render + Docker Compose + GitHub Actions CI/CD

## Repository Structure

- `backend/` main API, models, migrations, tests
- `frontend/` web app pages, modules, UI assets
- `Agro-copilot/` olive disease assistant service (integrated into main platform)
- `deploy/` production compose and deployment docs

## Local Run (Quick)

### 1) Agro Copilot
```powershell
cd Agro-copilot
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

### 2) Backend
```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3) Frontend
```powershell
cd frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd run dev
```

Open: `http://127.0.0.1:5173`

## Recruiter Note

This project is intentionally ambitious. The value is not only in features, but in how the system handles cross-domain complexity, role safety, deployment readiness, and practical AI integration in a high-friction real-world context.
