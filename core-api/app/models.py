from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey, func, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="sales_rep", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    #google_refresh_token = Column(String, nullable=True)
    connected_accounts = relationship("ConnectedAccount", back_populates="owner")

class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False, default="google")  # ex: "google"
    email = Column(String, index=True)
    refresh_token = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_history_id = Column(BigInteger, nullable=True)
    owner = relationship("User", back_populates="connected_accounts")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    deal_value = Column(Numeric(precision=10, scale=2), nullable=True)
    currency = Column(String(10), default="EUR", nullable=False)
    last_activity_description = Column(Text, nullable=True)
    intent_score = Column(Integer, nullable=True)
    last_researched_at = Column(DateTime(timezone=True), nullable=True)
    signals = Column(JSONB, default=list, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String, default="new", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    # action_type: "research" | "email" | "analysis" | "call" | "insight" — extensible
    action_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSONB, default=dict, nullable=False)
    status = Column(String, default="completed", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
