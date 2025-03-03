from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..db import get_db
from ..models.user import User
from ..models.review import EmployerReview, ReviewCreate, ReviewInDB
from .auth import get_current_active_user

router = APIRouter()

@router.post("", response_model=ReviewInDB)
async def create_employer_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit an employer review for an employee
    """
    # Check if employee exists
    employee = db.query(User).filter(User.id == review.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create new review
    db_review = EmployerReview(
        employee_id=review.employee_id,
        reviewer_id=current_user.id,
        performance_score=review.performance_score,
        communication_score=review.communication_score,
        teamwork_score=review.teamwork_score,
        innovation_score=review.innovation_score,
        leadership_score=review.leadership_score,
        technical_score=review.technical_score,
        reliability_score=review.reliability_score,
        comments=review.comments,
        review_period=review.review_period
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/{user_id}", response_model=List[ReviewInDB])
async def get_user_reviews(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all reviews for a specific employee
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if current user is the employee or has manager/admin role
    if current_user.id != user_id and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these reviews")
    
    reviews = db.query(EmployerReview).filter(EmployerReview.employee_id == user_id).all()
    return reviews 