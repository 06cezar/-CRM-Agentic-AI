from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class LeadBase(BaseModel):
    name: str
    company: str
    email: str
    status: Optional[str] = "cool"
    intent_score: Optional[float] = 0.0
    deal_value: Optional[float] = 0.0


class LeadCreate(LeadBase):
    pass


class LeadRead(LeadBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityRead(BaseModel):
    id: int
    lead_id: Optional[int] = None
    user_id: int
    action_type: str
    description: str
    created_at: datetime
    lead_name: Optional[str] = None

    class Config:
        from_attributes = True
