from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas

router = APIRouter(tags=["leads"])


@router.post("/", response_model=schemas.LeadRead, status_code=201)
def create_lead(
    lead_in: schemas.LeadCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    lead = models.Lead(
        name=lead_in.name,
        company=lead_in.company,
        email=lead_in.email,
        status=lead_in.status,
        intent_score=lead_in.intent_score,
        deal_value=lead_in.deal_value,
        owner_id=current_user.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=List[schemas.LeadRead])
def list_leads(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    leads = (
        db.query(models.Lead)
        .filter(models.Lead.owner_id == current_user.id)
        .order_by(models.Lead.intent_score.desc())
        .all()
    )
    return leads
