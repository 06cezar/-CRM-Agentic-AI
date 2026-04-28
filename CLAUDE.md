# CRM Agentic AI — Context for Claude

## What this project is

A CRM with AI agents that analyze sales leads in real time. The UI has 3 columns:
- **Activity Feed** — real-time log of AI agent actions
- **Intent Pipeline** — leads sorted by AI-calculated intent score (0–100)
- **Co-pilot Sidebar** — per-lead insights and draft message (EPIC 6, not yet implemented)

This is a university project (MDS course). Grading criteria: 2 AI agents (3 pts), dev process quality.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui |
| Core API | FastAPI + SQLAlchemy + Alembic + PostgreSQL |
| AI Service | FastAPI + Ollama (llama3.2:3b, runs locally) |
| Infra | Docker Compose (5 containers) |

---

## Repo structure

```
/
├── frontend/               # Next.js app
│   ├── app/                # Routes: /, /login, /register
│   ├── components/         # activity-feed, lead-pipeline, copilot-sidebar,
│   │                       # command-header, add-lead-modal, import-csv-modal
│   ├── components/ui/      # Only used shadcn components (badge, button, dialog,
│   │                       # input, label, scroll-area, separator, sheet, skeleton,
│   │                       # sonner, textarea, toggle)
│   ├── hooks/              # use-mobile.ts
│   └── lib/                # api.ts (all fetch calls), utils.ts
│
├── core-api/               # FastAPI backend
│   ├── app/
│   │   ├── models.py       # User, Lead, AgentActivity (SQLAlchemy)
│   │   ├── database.py     # DB engine + Base
│   │   ├── auth.py         # JWT helpers
│   │   └── routers/        # auth.py, leads.py, activity.py, stats.py
│   ├── alembic/            # DB migrations (2 migration files: 0001, 0002)
│   ├── main.py             # FastAPI app entrypoint
│   ├── entrypoint.sh       # Runs alembic upgrade head, then uvicorn
│   └── Dockerfile
│
├── ai-service/             # AI agent microservice
│   ├── agents/
│   │   └── research_agent.py  # LeadResearchAgent (Ollama + tool calls)
│   ├── routers/
│   │   └── research.py        # POST /research
│   ├── tests/              # 21 tests (unit + integration)
│   └── main.py
│
├── db/                     # Reserved for complex SQL queries (EPIC 6+)
│   └── README.md
│
└── docker-compose.yml      # 5 services: postgres, core-api, ai-service, frontend, ollama
```

---

## How to run

```bash
# Start everything
docker compose up -d

# Pull AI model (once, ~2GB)
docker exec crm-ollama ollama pull llama3.2:3b

# DB migrations run automatically via entrypoint.sh (no manual step needed)
```

URLs: frontend `localhost:3000`, core-api docs `localhost:8000/docs`, ai-service docs `localhost:8001/docs`

---

## Auth

HTTPOnly cookie-based JWT (not Bearer token in localStorage). Cookie is set on login, sent automatically on every request. Frontend `lib/api.ts` uses `credentials: "include"` on all fetch calls.

---

## Database models

```python
User        — id, email, hashed_password, role, created_at
Lead        — id, name, company, role, email, phone, score, deal_value,
              last_activity_description, signals (JSONB), created_at, updated_at
AgentActivity — id, user_id, action_type, description, metadata (JSONB), created_at
```

---

## AI Agent — LeadResearchAgent

Located in `ai-service/agents/research_agent.py`.

- Called via `POST /research` with a lead payload
- Uses Ollama (llama3.2:3b) with tool calling
- Tools: `set_intent_score` (0–100), `add_signal` (buying signal string)
- Returns: updated score + list of signals + summary text
- Core API (`POST /leads/{id}/research`) calls ai-service and persists the result
- Research is also auto-triggered in background on lead creation

---

## What's done (EPICs 1–5)

- **EPIC 1–2:** Auth (register/login/logout), JWT, protected routes
- **EPIC 3:** Lead CRUD (create, list, delete), PostgreSQL, Alembic migrations
- **EPIC 4:** LeadResearchAgent with Ollama, tool calls, intent score + signals
- **EPIC 5:** Full UI wiring — live pipeline, activity feed, dashboard stats, CSV import, auto-research on lead creation, toast notifications (sonner)

---

## What's NOT done yet (EPIC 6+)

- **Co-pilot Sidebar** — `winningArgument` and `draftMessage` fields exist on `Lead` interface but are always empty strings
- **Complex DB queries** — `db/` folder reserved for query objects, aggregations, paginated search
- **Second AI agent** — grading requires 2 agents; only LeadResearchAgent exists

---

## Important decisions / gotchas

- **Do NOT use `ignoreBuildErrors: true`** in `next.config.mjs` — it's set to `false`, TypeScript errors will fail the build
- **`entrypoint.sh` handles migrations** — no need to run `alembic upgrade head` manually
- **Only 2 Alembic migration files** (0001, 0002) — if you see "Multiple head revisions" error, old Docker images may have 4 migration files; run `docker compose build core-api`
- **Toast notifications use `sonner`** — not radix-ui toast (which was removed)
- **`db/Dockerfile` was replaced with `db/README.md`** — the folder is intentionally almost empty
- **`lead.status` does NOT exist** on the `Lead` TypeScript interface — use `lead.score` (number 0–100)
- **Ollama runs locally** — no API keys, no cloud costs; model is llama3.2:3b (~2GB)
- **LinkedIn scraping is legally risky** — use mock data or manual input for demo leads

---

## Key commands

```bash
docker compose up --build          # rebuild and start all containers
docker compose down                # stop (keeps data volumes)
docker compose down -v             # stop + DELETE all data (postgres volume)
docker compose logs core-api -f    # tail logs for a specific service
docker compose build frontend      # rebuild only frontend
```
