# CRM Agentic AI

Un CRM cu agenți AI care analizează lead-uri în timp real, calculează scorul de intenție și generează sugestii personalizate pentru vânzători.

Interfața are 3 coloane:
- **Activity Feed** — activitățile agenților AI în timp real
- **Intent Pipeline** — lead-urile sortate după scorul de intenție calculat de AI
- **Co-pilot Sidebar** — winning argument + draft mesaj personalizat per lead

---

## Funcționalități

- **Autentificare completă** — register, login/logout, verificare email, forgot/reset password
- **Lead Pipeline** — adaugă, vizualizează, șterge lead-uri; import CSV; scraper LinkedIn
- **4 Agenți AI:**
  - `LeadResearchAgent` — analizează profilul unui lead, extrage semnale de cumpărare, calculează scor de intenție 0–100 (pornit automat la crearea unui lead)
  - `CopilotAgent` — generează winning argument + draft email personalizat per lead (tier-based: HOT / WARM / COLD / LOST)
  - `SearchQueryAgent` — generează query-uri de căutare LinkedIn din ICP
  - `EmailClassifier` — clasifică emailuri primite prin Gmail
- **ICP Builder** — definești profilul clientului ideal în limbaj natural; AI-ul îl folosește la ranking
- **Gmail Integration** — conectare cont Google, monitorizare inbox prin Pub/Sub
- **Settings** — profil utilizator, conturi conectate, info platformă
- **Responsive** — funcționează pe mobile, tabletă și desktop
- **CI/CD** — GitHub Actions: lint → teste → build Docker → publish GHCR

---

## Pornire rapidă

### 1. Cerințe

**Windows / macOS**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalat și pornit

**Linux**
```bash
curl -fsSL https://get.docker.com | sh
sudo apt-get install -y docker-compose-plugin
sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
```

### 2. Clonează repo-ul

```bash
git clone https://github.com/vladinsc/-CRM-Agentic-AI.git
cd -CRM-Agentic-AI
```

### 3. Pornește serviciile

```bash
docker compose up -d
```

> Migrațiile bazei de date rulează automat la pornire.

### 4. Descarcă modelele AI (o singură dată)

```bash
docker exec crm-ollama ollama pull llama3.2:3b   # ~2GB — Research, Copilot, Email Classifier
docker exec crm-ollama ollama pull llama3.1:8b   # ~5GB — SearchQueryAgent
```

### 5. Accesează aplicația

| Serviciu | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Core API (docs) | http://localhost:8000/docs |
| AI Service (docs) | http://localhost:8001/docs |
| MinIO Console | http://localhost:9001 |

---

## Stack

| Layer | Tehnologie |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui |
| Core API | FastAPI + SQLAlchemy + Alembic + PostgreSQL |
| AI Service | FastAPI + Ollama (llama3.2:3b / llama3.1:8b) |
| Scraper | FastAPI + Playwright |
| Infra | Docker Compose (8 containere) |
| CI/CD | GitHub Actions + GHCR |

---

## Comenzi utile

```bash
docker compose up --build          # rebuild și pornește tot
docker compose down                # oprește (păstrează volumele)
docker compose down -v             # oprește + șterge toate datele
docker compose logs core-api -f    # urmărește logurile unui serviciu

# Teste
cd core-api && python -m pytest tests/ -q
cd ai-service && python -m pytest tests/ -q
```

---

## System Architecture Diagrams

### 1. High-Level Architecture
```mermaid
graph TD
    UI[Frontend: Next.js] --> API[Core API: FastAPI]
    API --> AI[AI Service: FastAPI]
    API --> Scraper[Scraper Service: FastAPI]
    
    API --> DB[(PostgreSQL)]
    API --> Storage[(MinIO)]
    
    AI --> Ollama[Ollama LLM]
    Scraper --> LinkedIn[LinkedIn]
    
    PubSub[Google Pub/Sub] --> API
    API --> Gmail[Gmail API]
```

### 2. Class Diagram (Data Models)
```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String role
    }
    
    class ConnectedAccount {
        +UUID id
        +UUID user_id
        +String provider
    }

    class Lead {
        +UUID id
        +String name
        +Integer intent_score
        +String status
    }

    class ScrapeJob {
        +UUID id
        +String query
        +String status
    }

    class AgentActivity {
        +UUID id
        +UUID lead_id
        +String action
    }

    class CopilotResult {
        +UUID id
        +UUID lead_id
        +Text sales_argument
    }

    class Email {
        +UUID id
        +String message_id
        +Boolean is_worth_saving
    }
    
    class ICPBlueprint {
        +UUID id
        +JSON criteria
    }

    User *-- ConnectedAccount
    User *-- Lead
    ScrapeJob *-- Lead
    Lead *-- AgentActivity
    Lead *-- CopilotResult
    Lead *-- Email
```

### 3. Lead Research Flow
```mermaid
sequenceDiagram
    participant UI as Frontend
    participant Core as Core API
    participant DB as PostgreSQL
    participant AI as AI Service
    participant LLM as Ollama

    UI->>Core: POST /leads/{id}/research
    Core->>DB: Fetch Lead Data
    DB-->>Core: Lead Record
    Core->>AI: POST /agent/research
    
    Note right of AI: ResearchAgent execution
    AI->>LLM: Prompt Evaluation
    LLM-->>AI: JSON Result
    
    AI-->>Core: Parsed Insights
    Core->>DB: Update Lead
    Core->>DB: Create AgentActivity
    Core-->>UI: 200 OK
```

### 4. LinkedIn Scraping Flow
```mermaid
sequenceDiagram
    participant UI as Frontend
    participant Core as Core API
    participant DB as PostgreSQL
    participant Scraper as Scraper Service
    participant LI as LinkedIn

    UI->>Core: POST /scraper/jobs
    Core->>DB: Create ScrapeJob
    Core->>Scraper: POST /jobs (async)
    Core-->>UI: 202 Accepted
    
    Scraper->>LI: Scrape Data
    
    loop Every Page
        LI-->>Scraper: HTML Data
        Scraper->>Core: POST /leads (Batch)
        Core->>DB: Save Leads
    end
    
    Scraper->>Core: PATCH /jobs (completed)
    Core->>DB: Update Status
```

### 5. Gmail Integration Flow
```mermaid
sequenceDiagram
    participant PubSub as Google Pub/Sub
    participant Core as Core API
    participant Gmail as Gmail API
    participant AI as AI Classifier
    participant MinIO as MinIO Storage
    participant DB as PostgreSQL

    PubSub->>Core: POST /gmail/webhook
    Core-->>PubSub: 200 OK
    
    Core->>Gmail: Fetch new messages
    Gmail-->>Core: Raw Email
    
    Core->>AI: evaluate_relevance()
    AI-->>Core: is_worth_saving
    
    alt is_worth_saving == True
        Core->>MinIO: Store Body
        Core->>DB: Save Metadata
    end
```
