6 phases, 14 new files, 8 modified files:

New container: scraper-service/
Dockerfile — Microsoft Playwright Python image (Chromium included)
scraper/linkedin.py — refactored POC: scrape_async() with page-by-page callback, --no-sandbox for Docker, AuthExpiredError on cookie expiry
scraper/job_runner.py — async orchestrator: marks job running → calls scraper → POSTs lead batches to core-api → marks completed/failed
main.py — POST /scrape (returns 202, fires background task), GET /health
Core-API
app/models.py — added linkedin_url to Lead, new LinkedInCredential and ScrapeJob models
app/routers/scraper.py — credentials CRUD, job management, internal lead-ingestion endpoint, AI query proxy
3 Alembic migrations (0009–0011)
AI Service — SearchQueryAgent (second agent for grading)
agents/search_query_agent.py — analyzes existing leads, suggests 3–5 Sales Navigator queries via suggest_search_queries tool
routers/search_agent.py — POST /agent/search-queries
Frontend
components/linkedin-scraper-modal.tsx — 3-tab modal: Credentials (cookie upload), Scrape (live progress bar, 3s polling), AI Suggest (query cards with "Use" button)
command-header.tsx — "Find Leads" button added
lib/api.ts — ScrapeJobAPI, SearchQuerySuggestion types + 6 new API methods
To run:

docker compose up --build
The INTERNAL_TOKEN was auto-generated and added to your .env. Migrations run automatically via entrypoint.sh.
