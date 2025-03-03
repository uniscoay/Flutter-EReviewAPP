from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import uuid

Base = declarative_base()

class PeerReview(Base):
    __tablename__ = "peer_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Tinder 风格点赞
    liked = Column(Boolean, default=False)
    is_anonymous = Column(Boolean, default=True)  # 是否匿名
    comments = Column(Text, nullable=True)  # 可选评论
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models
class PeerReviewBase(BaseModel):
    liked: bool = False
    is_anonymous: bool = True
    comments: Optional[str] = None

class PeerReviewCreate(PeerReviewBase):
    employee_id: str

class PeerReviewUpdate(BaseModel):
    liked: Optional[bool] = None
    comments: Optional[str] = None

class PeerReviewInDB(PeerReviewBase):
    id: str
    reviewer_id: str
    employee_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True 