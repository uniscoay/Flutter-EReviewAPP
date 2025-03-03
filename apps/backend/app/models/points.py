from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import uuid

Base = declarative_base()

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    image_url = Column(String)
    points_required = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    badge_id = Column(String, ForeignKey("badges.id"), nullable=False)
    awarded_at = Column(DateTime, default=datetime.utcnow)

class PointsTransaction(Base):
    __tablename__ = "points_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 可以是正数（获得）或负数（使用）
    action = Column(String, nullable=False)  # 例如："peer_review", "badge_award"
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic models
class BadgeBase(BaseModel):
    name: str
    description: str
    image_url: str
    points_required: int

class BadgeCreate(BadgeBase):
    pass

class BadgeInDB(BadgeBase):
    id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserBadgeCreate(BaseModel):
    user_id: str
    badge_id: str

class UserBadgeInDB(UserBadgeCreate):
    id: str
    awarded_at: datetime
    
    class Config:
        orm_mode = True

class PointsTransactionBase(BaseModel):
    amount: int
    action: str
    description: Optional[str] = None

class PointsTransactionCreate(PointsTransactionBase):
    user_id: str

class PointsTransactionInDB(PointsTransactionBase):
    id: str
    user_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True 