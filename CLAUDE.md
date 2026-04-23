# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CRM platform with agentic AI capabilities, consisting of three services: a Next.js frontend, a FastAPI core API, and a FastAPI AI service — all orchestrated via Docker Compose with a PostgreSQL database.

## Development Commands

### Run the full stack
```bash
docker-compose up
```

### Frontend (Next.js) — runs on port 3000
```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

### Core API (FastAPI) — runs on port 8000
```bash
cd core-api
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### AI Service (FastAPI) — runs on port 8001
```bash
cd ai-service
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Tests
```bash
# Core API
cd core-api && pytest

# AI Service
cd ai-service && pytest

# Single test file
pytest tests/test_main.py
```

### Database migrations (Alembic)
```bash
cd core-api
alembic upgrade head                                      # Apply migrations
alembic revision --autogenerate -m "description"         # New migration
```

## Architecture

### Services
- **frontend/** — Next.js 16 + React 19 + TypeScript. Sales team command center UI. Pages under `app/`, shared UI components under `components/ui/` (Radix UI primitives), feature components in `components/`. API calls are centralized in `lib/api.ts`, which reads `NEXT_PUBLIC_API_URL` and attaches Bearer tokens from `localStorage`.
- **core-api/** — FastAPI app with SQLAlchemy ORM. Handles auth and lead management. Routers live in `app/routers/` (`auth.py`, `leads.py`). Auth uses JWT (HS256, 24h expiry) with bcrypt password hashing. DB session injected via FastAPI dependency (`app/database.py`).
- **ai-service/** — Minimal FastAPI stub, currently just a health endpoint. Intended for AI/ML features.
- **db/** — Placeholder for database scripts.

### API Routes
- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `GET /api/v1/leads`, `POST /api/v1/leads` (owner-filtered by JWT identity)

### Data Flow
Frontend → Core API (HTTP + Bearer token) → PostgreSQL (SQLAlchemy ORM)

### Database
PostgreSQL 15. Models: `users`, `leads` (see `core-api/app/models.py`). Alembic migrations in `core-api/alembic/versions/`. Default connection: `postgresql://crm_user:crm_password@localhost:5432/crm_db` (override with `DATABASE_URL` env var).

## Key Environment Variables

| Variable | Service | Default |
|---|---|---|
| `DATABASE_URL` | core-api | `postgresql://crm_user:crm_password@localhost:5432/crm_db` |
| `SECRET_KEY` | core-api | `crm-secret-key-change-in-production` (**must be replaced in prod**) |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` |

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`):
1. **test_backend** — installs Python 3.11 deps for both services, runs `pytest` for each (DB is mocked)
2. **build-and-push** — builds and pushes Docker images to GHCR (`ghcr.io/{owner}/crm-{service}:latest`) on pushes to `main`

## Testing Notes

Backend tests mock SQLAlchemy engine to avoid requiring a live PostgreSQL instance in CI. Test client is FastAPI's `TestClient` (wraps httpx). `pytest.ini` in each service sets `pythonpath` so imports resolve correctly.
