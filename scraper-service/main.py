import os
import logging
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from scraper.job_runner import run_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")

app = FastAPI(title="CRM Scraper Service")


class ScrapeRequest(BaseModel):
    job_id: int
    user_id: int
    query: str
    pages: int
    cookies_json: str


@app.post("/scrape", status_code=202)
async def start_scrape(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
    x_internal_token: str = Header(...),
):
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")

    background_tasks.add_task(
        run_job,
        job_id=payload.job_id,
        user_id=payload.user_id,
        query=payload.query,
        pages=payload.pages,
        cookies_json=payload.cookies_json,
        core_api_url=CORE_API_URL,
        internal_token=INTERNAL_TOKEN,
    )

    return {"accepted": True, "job_id": payload.job_id}


@app.get("/health")
def health():
    return {"status": "healthy"}
