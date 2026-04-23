from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas

router = APIRouter(tags=["activities"])


@router.get("/", response_model=List[schemas.ActivityRead])
def list_activities(
    lead_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        db.query(models.Activity)
        .filter(models.Activity.user_id == current_user.id)
    )
    if lead_id is not None:
        query = query.filter(models.Activity.lead_id == lead_id)

    activities = query.order_by(models.Activity.created_at.desc()).limit(50).all()

    result = []
    for activity in activities:
        item = schemas.ActivityRead(
            id=activity.id,
            lead_id=activity.lead_id,
            user_id=activity.user_id,
            action_type=activity.action_type,
            description=activity.description,
            created_at=activity.created_at,
            lead_name=activity.lead.name if activity.lead else None,
        )
        result.append(item)
    return result
