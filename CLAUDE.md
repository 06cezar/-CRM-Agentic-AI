# CRM Agentic AI — Context for Claude

## Ce este proiectul

CRM cu agenți AI care analizează leads în timp real. UI cu 3 coloane:
- **Activity Feed** (stânga) — log live al acțiunilor agenților AI
- **Intent Pipeline** (centru) — leads sortate după scor de intenție (0–100)
- **Co-pilot Sidebar** (dreapta) — winning argument + draft email per lead

Proiect universitar (curs MDS). Criterii de notare: 2 agenți AI (3p), calitate proces dev.

---

## Stack

| Layer | Tehnologie |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui |
| Core API | FastAPI + SQLAlchemy + Alembic + PostgreSQL 15 |
| AI Service | FastAPI + Ollama (llama3.2:3b local, llama3.1:8b pentru search_query) |
| Scraper | FastAPI + Playwright (LinkedIn Sales Navigator) |
| Infra | Docker Compose (7 containere: postgres, core-api, ai-service, frontend, ollama, scraper-service, ngrok) |

---

## Structura repo

```
/
├── frontend/               # Next.js app
│   ├── app/                # Routes: /, /login, /register, /verify-email,
│   │                       #         /forgot-password, /reset-password, /settings,
│   │                       #         /api/auth/google/callback
│   ├── components/         # activity-feed, lead-pipeline, copilot-sidebar,
│   │                       # command-header, add-lead-modal, import-csv-modal,
│   │                       # linkedin-scraper-modal, get-connected-accounts
│   ├── components/ui/      # shadcn primitives
│   ├── hooks/              # useAuth.ts, use-mobile.ts
│   └── lib/                # api.ts (toate fetch-urile), utils.ts
│
├── core-api/               # FastAPI backend
│   ├── app/
│   │   ├── models.py       # User, ConnectedAccount, Lead, LinkedInCredential,
│   │   │                   # ScrapeJob, AgentActivity, CopilotResult
│   │   ├── database.py     # DB engine + Base
│   │   ├── auth.py         # JWT helpers, email send (fastapi_mail)
│   │   ├── config.py       # Settings (pydantic_settings, citit din .env)
│   │   ├── google_auth.py  # Google OAuth helpers
│   │   ├── gmail_watch.py  # Gmail Pub/Sub watch logic
│   │   └── routers/
│   │       ├── auth.py     # /auth/* (register, login, logout, me, verify-email,
│   │       │               #          forgot-password, reset-password)
│   │       ├── leads.py    # /leads (CRUD, /import CSV, /{id}/research)
│   │       ├── activity.py # /activity
│   │       ├── stats.py    # /stats
│   │       ├── copilot.py  # /leads/{id}/copilot, /leads/{id}/copilot/regenerate
│   │       ├── scraper.py  # /scraper/* (credentials, jobs, suggest-queries)
│   │       ├── google_auth.py # /api/auth/google/*
│   │       └── gmail_watcher.py # /api/gmail/*
│   ├── alembic/versions/   # 10 migration files (lanț linear: 0001→0011)
│   ├── main.py
│   ├── entrypoint.sh       # alembic upgrade head → uvicorn
│   └── Dockerfile
│
├── ai-service/             # AI agents microservice
│   ├── agents/
│   │   ├── research_agent.py    # LeadResearchAgent: scor intenție + semnale
│   │   ├── copilot_agent.py     # CopilotAgent: winning argument + draft email
│   │   └── search_query_agent.py # SearchQueryAgent: sugestii query LinkedIn
│   ├── routers/
│   │   ├── agent.py        # POST /agent/research, POST /agent/copilot
│   │   └── search_agent.py # POST /agent/search-queries
│   ├── tests/
│   │   ├── test_research_agent.py
│   │   └── test_copilot_agent_evals.py  # există dar incomplet
│   └── main.py
│
├── scraper-service/        # Playwright LinkedIn scraper
│   ├── scraper/
│   │   ├── linkedin.py     # Playwright automation (Sales Navigator)
│   │   └── job_runner.py   # Job execution + raportare progres la core-api
│   └── main.py
│
├── docker-compose.yml      # Prod-like config
├── docker-compose.override.yml  # Dev overrides (volume mounts + hot reload)
├── .env                    # NU se commitează — variabile locale
└── .github/workflows/ci-cd.yml  # CI: lint → test_core_api + test_ai_service
                                  #       + test_frontend → build_and_push
```

---

## Cum rulezi

```bash
docker compose up -d --build    # prima oară
docker compose up -d            # ulterior

# Pull model Ollama (o singură dată, ~2GB)
docker exec crm-ollama ollama pull llama3.2:3b

# Migrările se aplică automat prin entrypoint.sh
```

URL-uri: frontend `localhost:3000`, core-api docs `localhost:8000/docs`, ai-service `localhost:8001/docs`

---

## Auth

JWT în HTTPOnly cookie (`access_token`). Cookie setat la login, trimis automat pe fiecare request.
Frontend `lib/api.ts` folosește `credentials: "include"` pe toate fetch-urile.

**Email verification:** Auto-verificare la înregistrare dacă `MAIL_USERNAME` e gol în `.env`.

---

## Modele DB

```python
User              — id, email, hashed_password, full_name, role, is_verified, created_at
ConnectedAccount  — id, user_id, provider("google"), email, refresh_token,
                    last_history_id, is_watching, created_at
Lead              — id, name, company, role, email, phone, deal_value, currency,
                    last_activity_description, intent_score, last_researched_at,
                    signals(JSONB), assigned_to, status, linkedin_url, created_at
LinkedInCredential— id, user_id, cookies_json, uploaded_at, is_active
ScrapeJob         — id, user_id, query, pages_requested, status, scraped_count,
                    leads_created, error_message, started_at, completed_at, created_at
AgentActivity     — id, lead_id, lead_name, agent_name, action_type, message,
                    payload(JSONB), status, created_at
CopilotResult     — id, lead_id, winning_argument, draft_message, confidence,
                    model_used, generated_at, lead_snapshot(JSONB)
```

---

## Agenți AI

### LeadResearchAgent (`ai-service/agents/research_agent.py`)
- **Input:** lead dict (name, company, role, email, deal_value_display, last_activity_description)
- **Output:** `{ intent_score: 0-100, signals: ["..."], summary: "...", confidence: 0.0-1.0 }`
- **Model:** llama3.2:3b via Ollama (OpenAI-compatible API la `http://ollama:11434/v1`)
- **Pattern:** JSON prompting cu 3 retry-uri, fără tool calling

### CopilotAgent (`ai-service/agents/copilot_agent.py`)
- **Input:** lead dict + signals + intent_score
- **Output:** `{ winning_argument: "...", draft_message: "...", confidence: 0.0-1.0 }`
- **Model:** llama3.2:3b
- **Pattern:** JSON prompting cu 3 retry-uri, curăță placeholder-e ([YOUR NAME] etc.)

### SearchQueryAgent (`ai-service/agents/search_query_agent.py`)
- **Input:** lista de leads existente
- **Output:** `{ queries: [{ query, reasoning, expected_title }] }`
- **Model:** llama3.1:8b cu tool calling (`suggest_search_queries`)
- **Pattern:** Până la 4 iterații agentice, fallback la queries hardcodate

---

## Ce E implementat

| Feature | Status | Note |
|---|---|---|
| Lead CRUD + CSV import | ✅ | Suportă LinkedIn/HubSpot/Excel CSV |
| Research Agent (scor + semnale) | ✅ | Auto-trigger la creare lead |
| Copilot Agent (argument + email) | ✅ | Cache 24h, regenerare manuală |
| Search Query Agent | ✅ | Sugerează query-uri LinkedIn |
| Dashboard stats | ✅ | Hot leads, AI actions today, pipeline value |
| Activity feed | ✅ | Log live per agent |
| Google OAuth | ✅ | Stochează refresh_token în ConnectedAccount |
| Gmail Watch (setup) | ✅ | Pornire/oprire monitorizare inbox |
| LinkedIn Scraper (infra) | ✅ | Cookies upload, job queue, polling progres |
| Auth complet | ✅ | Register, login, logout, verify email, reset password |

---

## Ce NU E implementat (backlog)

| Feature | Fișier relevant | Detalii |
|---|---|---|
| **Gmail processing → leads** | `app/gmail_watch.py:64` | Extrage sender/subject dar nu creează activități sau linkează cu leads |
| **Send email din copilot** | — | Draft există în DB, buton de send lipsește |
| **ICP types + mesaje predefinite** | — | Nu există model Company sau ICP în DB |
| **Disconnect Google account** | `settings/page.tsx:75` | Alert "urmează să fie implementat" |
| **Agent evals** | `tests/test_copilot_agent_evals.py` | Fișier există, teste lipsesc |
| **CI funcțional end-to-end** | `.github/workflows/ci-cd.yml` | Pipeline există, necesită verificare |
| **Diagrame arhitectură** | — | Lipsesc complet |
| **Campanii email** | — | Long-term |

---

## Decizii importante / gotchas

- **`ignoreBuildErrors: false`** în `next.config.mjs` — erorile TypeScript fail-uiesc build-ul
- **`entrypoint.sh` rulează migrările** automat — nu rula `alembic upgrade head` manual
- **Lanț Alembic linear:** `0001→0002→0003→21270b3f4b2a→427ef9caafac→ec86383315c7→a8faead918b5→0009→0010→0011`
- **AI Service port:** intern rulează pe `:8000`, mapare docker `8001:8000`. Din rețeaua Docker, core-api apelează `http://ai-service:8000`
- **Toast-uri:** folosesc `sonner`, NU radix-ui toast
- **`lead.status` există în DB** (default "new") dar UI-ul folosește `lead.score` pentru filtrare
- **Ollama local** — fără API keys, fără costuri cloud; model llama3.2:3b (~2GB)
- **LinkedIn scraping risc legal** — folosiți date mock sau input manual pentru demo
- **Email verification skip:** dacă `MAIL_USERNAME` e gol în `.env`, utilizatorii sunt auto-verificați la înregistrare
- **`ngrok` restart: no** în docker-compose — nu are authtoken, nu repornește la infinit

---

## Variabile de mediu (`.env` la rădăcina repo)

```env
DATABASE_URL=postgresql://crm_user:crm_password@db:5432/crm_db
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
AI_SERVICE_URL=http://ai-service:8000   # portul intern Docker, NU 8001
SECRET_KEY=<random-string>
INTERNAL_TOKEN=<token-scraper>
NGROK_AUTHTOKEN=                        # opțional, lasă gol pentru dev
GOOGLE_CREDENTIALS_JSON={}
MAIL_USERNAME=                          # gol = skip verificare email
MAIL_PASSWORD=
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME=CRM
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
```

---

## Comenzi cheie

```bash
docker compose up --build             # rebuild + start
docker compose down                   # stop (păstrează date)
docker compose down -v                # stop + ȘTERGE date postgres
docker compose up -d --build core-api # rebuild doar core-api
docker compose logs core-api -f       # tail logs serviciu specific
docker compose restart core-api       # restart fără rebuild

# Verifică/activează useri în DB
docker exec crm-postgres psql -U crm_user -d crm_db \
  -c "UPDATE users SET is_verified=true WHERE is_verified IS NULL OR is_verified=false;"
```
