# Worker Radar — System Architecture Map

## 🧠 Vision

Worker Radar is a scalable platform that connects workers and employers in real time using a **worker-first model**:

* Workers publish availability
* Employers instantly discover and contact them

The system must support **real-time availability, high traffic, and geographic expansion**.

---

## 🏗️ System Architecture (High-Level)

Frontend (Web / Mobile)
↓
API Gateway (FastAPI)
↓
Core Services Layer
↓
Database (PostgreSQL)
↓
Cache Layer (Redis)
↓
Async Workers (Background Jobs)

---

## 📦 Core Modules (Separation of Concerns)

### 1. Worker Service

Responsible for:

* Worker creation
* Worker profile management
* Team size management

---

### 2. Availability Service

Responsible for:

* Worker availability status (real-time)
* Status updates (Available / Busy)
* Time-based availability

---

### 3. Search & Matching Service

Responsible for:

* Filtering workers (location, availability, price)
* Ranking workers
* Fast queries

---

### 4. Contact Layer

Responsible for:

* Call links
* WhatsApp integration

(No messaging system in MVP)

---

## 🗄️ Database Design (PostgreSQL)

### workers table

* id (UUID, primary key)
* name (string)
* phone (string)
* village (string, indexed)
* price_per_day (numeric)
* team_size (integer)
* available (boolean, indexed)
* created_at (timestamp)

---

### indexing strategy

* index on (available)
* index on (village)
* optional composite index (village + available)

---

## 🔌 API Design

### Worker APIs

* POST /workers → create worker
* GET /workers → list workers
* GET /workers?available=true → filter available
* GET /workers?village=X → filter by location

---

### Availability APIs

* PATCH /workers/{id}/availability → update status

---

## ⚡ Performance Strategy

* Use PostgreSQL for reliable storage
* Use Redis for:

  * caching worker lists
  * fast availability queries
* Avoid heavy joins
* Keep queries simple and indexed

---

## 🔄 Real-Time Strategy

Phase 1:

* polling (frontend refresh every few seconds)

Phase 2:

* WebSockets for live updates

---

## 📱 Frontend Structure

### Pages:

1. Worker Registration Page
2. Worker List Page
3. Filters (availability + village)

---

### UX Rules:

* Mobile-first
* Minimal clicks
* Large buttons
* Fast loading

---

## 🚀 Deployment Architecture

* Backend: Docker container
* API: FastAPI server
* Database: Managed PostgreSQL (Supabase / Neon)
* Cache: Redis (optional early, required later)

---

## 📈 Scaling Strategy

### Phase 1 (MVP)

* Monolith backend
* Single database

### Phase 2 (Growth)

* Add Redis caching
* Optimize queries

### Phase 3 (Scale)

* Split into services:

  * Worker Service
  * Matching Service
  * Notification Service

---

## 🧠 Engineering Principles

* Keep modules independent
* Avoid tight coupling
* Build for extension, not complexity
* Prefer simple solutions that scale

---

## 🚫 Constraints

Do NOT:

* Add unnecessary features
* Introduce microservices early
* Use complex infrastructure prematurely

---

## 🏁 Success Criteria

System is successful when:

* Workers can register easily
* Workers can update availability quickly
* Employers can find workers instantly
* System responds fast (<1s query time)

---

## ⚡ Guiding Rule

> Build a system that can scale, but ship something usable immediately
