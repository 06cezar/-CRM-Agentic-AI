# CRM Agentic AI — Context for Claude

## What this project is

A CRM with AI agents that analyze sales leads in real time. The UI has 3 columns:
- **Activity Feed** — real-time log of AI agent actions
- **Intent Pipeline** — leads sorted by AI-calculated intent score (0–100)
- **Co-pilot Sidebar** — per-lead winning argument + draft message (implemented)

Also includes: ICP Builder, LinkedIn lead scraper, Gmail integration, email classification.

This is a university project (MDS course). Grading criteria: 2 AI agents (3 pts), dev process quality.
**Currently has 4 AI agents** — well above the minimum.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui |
| Core API | FastAPI + SQLAlchemy + Alembic + PostgreSQL |
| AI Service | FastAPI + Ollama (llama3.2:3b, runs locally) |
| Scraper | FastAPI + Playwright (LinkedIn scraping) |
| Infra | Docker Compose (8 containers) |

---

## Repo structure

```
/
├── frontend/
│   ├── app/                # Routes: /, /login, /register, /icp, /settings,
│   │                       # /forgot-password, /reset-password, /verify-email
│   ├── components/         # activity-feed, lead-pipeline, copilot-sidebar,
│   │                       # command-header, add-lead-modal, import-csv-modal,
│   │                       # linkedin-scraper-modal, icp-builder-form,
│   │                       # get-connected-accounts
│   ├── components/ui/      # shadcn components
│   ├── hooks/              # use-mobile.ts
│   └── lib/                # api.ts (all fetch calls), utils.ts
│
├── core-api/
│   ├── app/
│   │   ├── models.py       # 9 models (see Database Models section)
│   │   ├── database.py     # DB engine + Base
│   │   ├── auth.py         # JWT helpers, email verification, password reset
│   │   ├── config.py       # pydantic-settings — reads .env and ../.env
│   │   ├── gmail_watch.py  # Gmail Pub/Sub listener (partially implemented)
│   │   ├── services/
│   │   │   ├── ai_classifier.py  # Email intent classifier (Ollama)
│   │   │   └── s3_service.py     # MinIO storage for emails
│   │   └── routers/        # 10 routers (see API section)
│   ├── alembic/versions/   # 3 migration files (hash-named, linear chain)
│   ├── tests/              # 74 tests (unit + integration, no real DB needed)
│   ├── main.py
│   ├── entrypoint.sh       # runs alembic upgrade head, then uvicorn
│   └── Dockerfile
│
├── ai-service/
│   ├── agents/
│   │   ├── research_agent.py    # LeadResearchAgent
│   │   ├── copilot_agent.py     # CopilotAgent
│   │   └── search_query_agent.py # SearchQueryAgent
│   ├── routers/
│   │   ├── agent.py             # POST /agent/research, POST /agent/copilot
│   │   └── search_agent.py      # POST /agent/search-queries
│   ├── tests/              # unit + integration tests
│   └── main.py
│
├── scraper-service/
│   ├── scraper/
│   │   ├── linkedin.py     # Playwright LinkedIn scraper
│   │   └── job_runner.py   # background job runner
│   └── main.py
│
└── docker-compose.yml      # 8 services: frontend, core-api, ai-service,
                            # scraper-service, ollama, postgres, minio, ngrok
```

---

## How to run

```bash
# Start everything
docker compose up -d

# Pull AI models (once)
docker exec crm-ollama ollama pull llama3.2:3b   # ~2GB, used by research + copilot + email classifier
docker exec crm-ollama ollama pull llama3.1:8b   # used by SearchQueryAgent

# DB migrations run automatically via entrypoint.sh
```

URLs:
- Frontend: `localhost:3000`
- Core API docs: `localhost:8000/docs`
- AI Service docs: `localhost:8001/docs`
- MinIO console: `localhost:9001` (minioadmin / minioadmin)

---

## Auth

HTTPOnly cookie-based JWT. Cookie set on login/register, sent automatically on every request.
Frontend `lib/api.ts` uses `credentials: "include"` on all fetch calls.

**Known bug**: register endpoint issues JWT with `sub=user.email` but `get_current_user`
does `int(user_id)` — any authenticated call right after register will 401.
Login works correctly (`sub=user.id`). Fix: change `auth.py:59` to `sub=str(user.id)`.

---

## Database models

```python
User             — id, email, full_name, hashed_password, role, is_verified, created_at
ConnectedAccount — id, user_id, email, google_refresh_token, last_history_id, is_watching
Lead             — id, name, company, role, email, phone, deal_value, currency,
                   intent_score, last_activity_description, signals (JSONB),
                   assigned_to, status, linkedin_url, last_researched_at, created_at
LinkedInCredential — id, user_id, li_at_cookie, created_at
ScrapeJob        — id, user_id, queries (JSONB), status, results (JSONB), created_at
AgentActivity    — id, lead_id, lead_name, agent_name, action_type, message,
                   payload (JSONB), status, created_at
CopilotResult    — id, lead_id (unique), winning_argument, draft_message,
                   confidence, model_used, generated_at, lead_snapshot (JSONB)
ICPBlueprint     — id, user_id, raw_inputs (JSONB), structured_data (JSONB),
                   is_active, created_at, updated_at
Email            — id, user_id, lead_id, email_id (unique), subject,
                   s3_path, ai_reasoning, classification_score, created_at
```

**Migrations** (3 files, linear chain, no multi-head):
- `452eec4966e0_fix.py` — base (users → leads → activities → copilot_results etc.)
- `b7b364e79bcc_add_icp_blueprint.py`
- `bb812b415554_added_email_storing_logic.py`

**Important**: `lead.score` in frontend = `intent_score` in DB, mapped via alias in `LeadResponse`.

---

## AI Agents (4 total)

| Agent | File | Model | Endpoint | Auto-triggered? |
|---|---|---|---|---|
| **LeadResearchAgent** | `ai-service/agents/research_agent.py` | llama3.2:3b | `POST /agent/research` | Yes — on lead create (background) |
| **CopilotAgent** | `ai-service/agents/copilot_agent.py` | llama3.2:3b | `POST /agent/copilot` | Yes — chained after research (24h cache) |
| **SearchQueryAgent** | `ai-service/agents/search_query_agent.py` | llama3.1:8b | `POST /agent/search-queries` | No — called from scraper modal |
| **EmailClassifier** | `core-api/app/services/ai_classifier.py` | llama3.2:3b | internal | Partially — webhook exists but Gmail→classifier pipeline incomplete |

LeadResearchAgent uses JSON-prompting (not Ollama tool_use format).
CopilotAgent uses same JSON-prompting approach.
SearchQueryAgent uses OpenAI-compatible tool calls via Ollama.

---

## Core API — Routers (10 total)

| Router | Prefix | Key endpoints |
|---|---|---|
| auth | `/auth` | register, verify-email, login, logout, me, forgot-password, reset-password |
| leads | `/leads` | CRUD + import CSV + `/research` + `/copilot` |
| activity | `/activity` | GET list |
| stats | `/stats` | GET dashboard stats |
| copilot | *(no prefix)* | `GET /leads/{id}/copilot`, `POST /leads/{id}/copilot/regenerate` |
| icp | `/icp` | POST / GET (create + list blueprints) |
| google_auth | `/api/auth/google` | OAuth login/callback, get accounts, Pub/Sub webhook |
| gmail_watcher | `/api/gmail` | watch, status, set-status — ⚠️ `restart_watch` calls undefined function |
| scraper | `/scraper` | credentials CRUD, jobs CRUD, `POST /suggest-queries` |
| emails | `/emails` | `POST /webhook` (stores + classifies incoming emails) |

---

## Frontend pages

| Route | Component | Notes |
|---|---|---|
| `/` | main dashboard | 3-column layout: activity feed + pipeline + copilot |
| `/login`, `/register` | auth forms | |
| `/forgot-password`, `/reset-password`, `/verify-email` | auth flows | |
| `/icp` | `icp-builder-form.tsx` | fully wired to `POST/GET /icp/` |
| `/settings` | `get-connected-accounts.tsx` | Google account connection — ⚠️ badge broken (see gotchas) |

---

## Tests

**core-api** (74 tests, run from `core-api/`):
```bash
python -m pytest tests/ -q
```
- `test_auth_unit.py` — hash_password, verify_password, create_access_token (pure unit)
- `test_auth_api.py` — register/login/logout/me endpoints
- `test_leads_unit.py` — _format_deal_value, _map_row helpers
- `test_leads_api.py` — full CRUD + CSV import
- `test_icp_api.py` — ICP create/get
- `test_main.py` — health check

All tests mock DB with `app.dependency_overrides` + MagicMock — no PostgreSQL needed.
`config.py` reads `.env` from `(".env", "../.env")` — works in CI and locally.

**ai-service** (run from `ai-service/`):
```bash
python -m pytest tests/ -q           # unit tests only
python -m pytest tests/ -m integration  # requires running Ollama
```

---

## Known issues / gotchas

- **`auth.py:59`** — register issues JWT with `sub=user.email`, should be `sub=str(user.id)`.
  Any authed request right after register → 401. Login is fine.

- **`gmail_watcher.py:112`** — `restart_watch` endpoint calls undefined `activate_gmail_account_watch`.
  `POST /api/gmail/watch/{account_id}` → 500 on call.

- **`gmail_watch.py:77`** — Gmail → classifier pipeline is plumbed but disconnected.
  Pub/Sub webhook receives emails, then only `print()`s them. Classifier is never called.

- **`settings/page.tsx:30`** — checks `userData.google_refresh_token` to show "Connected" badge,
  but `/auth/me` never returns that field. Badge never shows. Real state is in `/api/auth/google/get_connected_accounts`.

- **SearchQueryAgent default model is `llama3.1:8b`** — if not pulled, agent returns hardcoded
  fallback queries silently. Pull with: `docker exec crm-ollama ollama pull llama3.1:8b`

- **Do NOT use `ignoreBuildErrors: true`** in `next.config.mjs` — TypeScript errors fail build.

- **Toast notifications use `sonner`** — not radix-ui toast.

- **`lead.status` does NOT exist** on `Lead` TypeScript interface — use `lead.score` (0–100).

- **MinIO credentials** hardcoded in `docker-compose.yml` (minioadmin/minioadmin) — fine for local dev.

---

## Key commands

```bash
docker compose up --build            # rebuild and start all
docker compose down                  # stop (keeps volumes)
docker compose down -v               # stop + delete all data
docker compose logs core-api -f      # tail logs for a service
docker compose build core-api        # rebuild only one service

# Run tests locally
cd core-api && python -m pytest tests/ -q
cd ai-service && python -m pytest tests/ -q
```
