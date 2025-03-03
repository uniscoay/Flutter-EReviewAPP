from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
import uuid

Base = declarative_base()

class EmployerReview(Base):
    __tablename__ = "employer_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 7 评分字段 (1-5 分)
    performance_score = Column(Float)  # 工作表现
    communication_score = Column(Float)  # 沟通能力
    teamwork_score = Column(Float)  # 团队合作
    innovation_score = Column(Float)  # 创新能力
    leadership_score = Column(Float)  # 领导能力
    technical_score = Column(Float)  # 技术能力
    reliability_score = Column(Float)  # 可靠性
    
    comments = Column(Text)  # 评论
    review_period = Column(String)  # 评审期间 (如 "2023 Q1")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models
class ReviewBase(BaseModel):
    performance_score: float = Field(..., ge=1, le=5)
    communication_score: float = Field(..., ge=1, le=5)
    teamwork_score: float = Field(..., ge=1, le=5)
    innovation_score: float = Field(..., ge=1, le=5)
    leadership_score: float = Field(..., ge=1, le=5)
    technical_score: float = Field(..., ge=1, le=5)
    reliability_score: float = Field(..., ge=1, le=5)
    comments: Optional[str] = None
    review_period: str

class ReviewCreate(ReviewBase):
    employee_id: str

class ReviewUpdate(BaseModel):
    performance_score: Optional[float] = Field(None, ge=1, le=5)
    communication_score: Optional[float] = Field(None, ge=1, le=5)
    teamwork_score: Optional[float] = Field(None, ge=1, le=5)
    innovation_score: Optional[float] = Field(None, ge=1, le=5)
    leadership_score: Optional[float] = Field(None, ge=1, le=5)
    technical_score: Optional[float] = Field(None, ge=1, le=5)
    reliability_score: Optional[float] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    review_period: Optional[str] = None

class ReviewInDB(ReviewBase):
    id: str
    employee_id: str
    reviewer_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True 