import os
import json
import logging
import threading
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Lead, LinkedInCredential, ScrapeJob
from app.auth import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://scraper-service:8002")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")

router = APIRouter(prefix="/scraper", tags=["scraper"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CredentialsUpload(BaseModel):
    cookies_json: str


class ScrapeJobCreate(BaseModel):
    query: str
    pages: int = 2


class ScrapeJobResponse(BaseModel):
    id: int
    query: str
    pages_requested: int
    status: str
    scraped_count: int
    leads_created: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScrapedLeadItem(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    profile_url: Optional[str] = None


class InternalLeadsPayload(BaseModel):
    leads: list[ScrapedLeadItem]


class InternalJobPatch(BaseModel):
    status: Optional[str] = None
    scraped_count: Optional[int] = None
    leads_created: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Internal token guard ──────────────────────────────────────────────────────

def _verify_internal_token(x_internal_token: str = Header(...)):
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dispatch_scrape_job(job_id: int, user_id: int, query: str, pages: int, cookies_json: str) -> None:
    """Call the scraper-service to kick off the job. Runs in a background thread."""
    payload = {
        "job_id": job_id,
        "user_id": user_id,
        "query": query,
        "pages": pages,
        "cookies_json": cookies_json,
    }
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{SCRAPER_SERVICE_URL}/scrape", json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to dispatch scrape job {job_id} to scraper-service: {e}")
        db = SessionLocal()
        try:
            job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = f"Scraper service unreachable: {str(e)}"
                db.commit()
        finally:
            db.close()


def _run_research_thread(lead_id: int) -> None:
    """Trigger research for a scraped lead in a background thread."""
    from app.routers.leads import _run_research_in_background
    _run_research_in_background(lead_id)


# ── Credentials endpoints ─────────────────────────────────────────────────────

@router.post("/credentials", status_code=201)
def upload_credentials(
    body: CredentialsUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload LinkedIn session cookies for the current user."""
    try:
        json.loads(body.cookies_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="cookies_json must be valid JSON")

    cred = db.query(LinkedInCredential).filter(
        LinkedInCredential.user_id == current_user.id
    ).first()

    if cred:
        cred.cookies_json = body.cookies_json
        cred.uploaded_at = datetime.now(timezone.utc)
        cred.is_active = True
    else:
        cred = LinkedInCredential(
            user_id=current_user.id,
            cookies_json=body.cookies_json,
            is_active=True,
        )
        db.add(cred)

    db.commit()
    return {"status": "saved"}


@router.get("/credentials/status")
def get_credentials_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if the current user has active LinkedIn credentials."""
    cred = db.query(LinkedInCredential).filter(
        LinkedInCredential.user_id == current_user.id,
        LinkedInCredential.is_active == True,
    ).first()
    return {"has_credentials": cred is not None}


@router.delete("/credentials", status_code=204)
def delete_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate stored LinkedIn credentials."""
    cred = db.query(LinkedInCredential).filter(
        LinkedInCredential.user_id == current_user.id
    ).first()
    if cred:
        cred.is_active = False
        db.commit()


# ── Scrape job endpoints ──────────────────────────────────────────────────────

@router.post("/jobs", response_model=ScrapeJobResponse, status_code=201)
def create_scrape_job(
    body: ScrapeJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new LinkedIn Sales Navigator scrape job."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if not (1 <= body.pages <= 10):
        raise HTTPException(status_code=400, detail="Pages must be between 1 and 10")

    cred = db.query(LinkedInCredential).filter(
        LinkedInCredential.user_id == current_user.id,
        LinkedInCredential.is_active == True,
    ).first()
    if not cred:
        raise HTTPException(status_code=400, detail="No active LinkedIn credentials. Upload cookies first.")

    job = ScrapeJob(
        user_id=current_user.id,
        query=body.query.strip(),
        pages_requested=body.pages,
        status="pending",
        scraped_count=0,
        leads_created=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cookies_json = cred.cookies_json
    threading.Thread(
        target=_dispatch_scrape_job,
        args=(job.id, current_user.id, job.query, job.pages_requested, cookies_json),
        daemon=True,
    ).start()

    return job


@router.get("/jobs", response_model=list[ScrapeJobResponse])
def list_scrape_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List scrape jobs for the current user (most recent first)."""
    jobs = (
        db.query(ScrapeJob)
        .filter(ScrapeJob.user_id == current_user.id)
        .order_by(ScrapeJob.created_at.desc())
        .limit(20)
        .all()
    )
    return jobs


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
def get_scrape_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll progress of a specific scrape job."""
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Internal endpoints (called by scraper-service) ────────────────────────────

@router.post("/jobs/{job_id}/leads")
def receive_scraped_leads(
    job_id: int,
    body: InternalLeadsPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: str = Depends(_verify_internal_token),
):
    """
    Internal endpoint: scraper-service posts batches of scraped leads here.
    Deduplicates, creates Lead rows, triggers research for each new lead.
    """
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    user_id = job.user_id
    accepted = 0
    skipped = 0

    for item in body.leads:
        if not item.name:
            skipped += 1
            continue

        # Primary dedup: linkedin_url
        if item.profile_url:
            exists = db.query(Lead).filter(
                Lead.linkedin_url == item.profile_url,
                Lead.assigned_to == user_id,
            ).first()
            if exists:
                skipped += 1
                continue

        # Fallback dedup: name + company
        if item.name and item.company:
            exists = db.query(Lead).filter(
                Lead.name == item.name,
                Lead.company == item.company,
                Lead.assigned_to == user_id,
            ).first()
            if exists:
                skipped += 1
                continue

        placeholder_email = f"scraped_li_{uuid4().hex[:8]}@placeholder.invalid"
        note = f"Scraped from LinkedIn Sales Navigator"
        if item.location:
            note += f" · {item.location}"

        lead = Lead(
            name=item.name,
            company=item.company or "—",
            role=item.title or "—",
            email=placeholder_email,
            last_activity_description=note,
            linkedin_url=item.profile_url,
            status="new",
            assigned_to=user_id,
        )
        db.add(lead)
        db.flush()

        threading.Thread(
            target=_run_research_thread,
            args=(lead.id,),
            daemon=True,
        ).start()

        accepted += 1

    job.leads_created = (job.leads_created or 0) + accepted
    db.commit()

    return {"accepted": accepted, "skipped": skipped}


@router.patch("/jobs/{job_id}")
def update_scrape_job(
    job_id: int,
    body: InternalJobPatch,
    db: Session = Depends(get_db),
    _: str = Depends(_verify_internal_token),
):
    """Internal endpoint: scraper-service updates job status/progress."""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    db.commit()
    return {"ok": True}


# ── AI search query suggestions ───────────────────────────────────────────────

@router.post("/suggest-queries")
def suggest_search_queries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proxy: fetch user's leads and ask the AI to suggest search queries."""
    leads = (
        db.query(Lead)
        .filter(Lead.assigned_to == current_user.id)
        .order_by(Lead.created_at.desc())
        .limit(20)
        .all()
    )

    leads_payload = [
        {
            "name": lead.name,
            "company": lead.company,
            "role": lead.role,
            "signals": lead.signals or [],
        }
        for lead in leads
    ]

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{AI_SERVICE_URL}/agent/search-queries",
                json={"leads": leads_payload},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"AI service unavailable: {str(e)}")
