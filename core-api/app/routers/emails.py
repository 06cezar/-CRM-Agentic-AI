from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Email
from app.services.s3_service import save_email_to_s3
from app.services.ai_classifier import classify_incoming_email
from pydantic import BaseModel
from typing import Optional, Any, Dict
import logging

router = APIRouter(prefix="/emails", tags=["Emails"])
logger = logging.getLogger(__name__)

class EmailWebhookPayload(BaseModel):
    user_id: int
    lead_id: Optional[int] = None
    email_id: str
    subject: str
    body: str
    raw_payload: Dict[str, Any]

async def handle_email_processing(payload: EmailWebhookPayload):
    """
    Background task to handle AI classification and storage.
    """
    # Create a new DB session since this runs in the background
    db = SessionLocal()
    try:
        # 1. Classify email using Ollama
        classification = await classify_incoming_email(payload.subject, payload.body)
        
        if not classification.is_worth_saving:
            logger.info(f"Email {payload.email_id} rejected by AI. Reason: {classification.reasoning}")
            return

        # 2. Save to S3 (MinIO)
        try:
            s3_path = await save_email_to_s3(
                user_id=payload.user_id,
                lead_id=payload.lead_id or 0,
                email_id=payload.email_id,
                email_data=payload.raw_payload
            )
        except Exception as e:
            logger.error(f"Failed to save email to S3 in background: {str(e)}")
            return

        # 3. Save metadata and AI reasoning to PostgreSQL
        try:
            new_email_record = Email(
                user_id=payload.user_id,
                lead_id=payload.lead_id,
                email_id=payload.email_id,
                subject=payload.subject,
                s3_path=s3_path,
                ai_reasoning=classification.reasoning,
                classification_score=classification.confidence_score
            )
            
            db.add(new_email_record)
            db.commit()
            
        except Exception as e:
            logger.error(f"Database error while saving email record in background: {str(e)}")
            db.rollback()
            
    finally:
        db.close()

@router.post("/webhook")
async def process_incoming_email_webhook(
    payload: EmailWebhookPayload,
    background_tasks: BackgroundTasks
):
    """
    Receives raw email payload and acknowledges receipt immediately.
    Processing (AI + S3) happens in the background.
    """
    background_tasks.add_task(handle_email_processing, payload)
    
    return {
        "status": "accepted",
        "message": "Email processing started in background"
    }
