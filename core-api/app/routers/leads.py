from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
import os
import httpx
from app.database import get_db
from app.models import Lead, AgentActivity, User
from app.auth import get_current_user

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

router = APIRouter(prefix="/leads", tags=["leads"])

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "RON": "RON "}


# ── Schemas ──────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    name: str
    company: str
    role: str
    email: str
    phone: Optional[str] = None
    deal_value: Optional[Decimal] = None
    currency: str = "EUR"
    last_activity_description: Optional[str] = None
    status: str = "new"


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    deal_value: Optional[Decimal] = None
    currency: Optional[str] = None
    last_activity_description: Optional[str] = None
    status: Optional[str] = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str
    role: str
    email: str
    phone: Optional[str]
    deal_value: Optional[Decimal]
    currency: str
    last_activity_description: Optional[str]
    intent_score: Optional[int]
    last_researched_at: Optional[datetime]
    signals: list
    assigned_to: Optional[int]
    status: str
    created_at: datetime

    @computed_field
    @property
    def score(self) -> Optional[int]:
        """Alias for intent_score — used by frontend."""
        return self.intent_score

    @computed_field
    @property
    def deal_value_display(self) -> Optional[str]:
        """Pre-formatted deal value for frontend (e.g. '€45,000')."""
        if self.deal_value is None:
            return None
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency + " ")
        return f"{symbol}{int(self.deal_value):,}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[LeadResponse])
def list_leads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all leads assigned to the current user, sorted by intent_score DESC."""
    leads = (
        db.query(Lead)
        .filter(Lead.assigned_to == current_user.id)
        .order_by(Lead.intent_score.desc().nulls_last())
        .all()
    )
    return leads


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    body: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new lead assigned to the current user."""
    lead = Lead(**body.model_dump(), assigned_to=current_user.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single lead by ID."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.assigned_to == current_user.id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.assigned_to == current_user.id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.assigned_to == current_user.id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()


@router.post("/{lead_id}/research", response_model=LeadResponse)
def research_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Declanșează LeadResearchAgent pentru un lead.
    Apelează ai-service, persistă rezultatele și returnează lead-ul îmbogățit.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.assigned_to == current_user.id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # ── Apelează ai-service ───────────────────────────────────────────────────
    payload = {
        "id": lead.id,
        "name": lead.name,
        "company": lead.company,
        "role": lead.role,
        "email": lead.email,
        "deal_value_display": f"€{int(lead.deal_value):,}" if lead.deal_value else None,
        "last_activity_description": lead.last_activity_description,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{AI_SERVICE_URL}/agent/research", json=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"AI service unavailable: {str(e)}")

    # ── Persistă rezultatele în leads ────────────────────────────────────────
    lead.intent_score = result["intent_score"]
    lead.signals = result["signals"]
    lead.last_researched_at = datetime.now(timezone.utc)

    # ── Inserează în agent_activities ────────────────────────────────────────
    activity = AgentActivity(
        lead_id=lead.id,
        lead_name=lead.name,
        agent_name="LeadResearchAgent",
        action_type="research",
        message=result["summary"],
        payload=result,
        status="completed",
    )
    db.add(activity)
    db.commit()
    db.refresh(lead)

    return lead
