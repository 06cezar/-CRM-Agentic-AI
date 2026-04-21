from sqlalchemy import Column, Integer, String, DateTime, func, Float, ForeignKey
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
    leads = relationship("Lead", back_populates="owner", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    status = Column(String, default="cool", nullable=False)
    intent_score = Column(Float, default=0.0, nullable=False)
    deal_value = Column(Float, default=0.0, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="leads")