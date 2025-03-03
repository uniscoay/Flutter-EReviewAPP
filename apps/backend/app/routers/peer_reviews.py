from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import asyncio

from ..db import get_db
from ..models.user import User
from ..models.peer_review import PeerReview, PeerReviewCreate, PeerReviewInDB
from ..models.points import PointsTransaction
from .auth import get_current_active_user
from .realtime import broadcast_like_update

router = APIRouter()

@router.post("", response_model=PeerReviewInDB)
async def create_peer_review(
    review: PeerReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit a peer review for an employee
    """
    # Check if employee exists
    employee = db.query(User).filter(User.id == review.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Prevent self-review
    if current_user.id == review.employee_id:
        raise HTTPException(status_code=400, detail="Cannot review yourself")
    
    # Check if review already exists
    existing_review = db.query(PeerReview).filter(
        PeerReview.reviewer_id == current_user.id,
        PeerReview.employee_id == review.employee_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this employee")
    
    # Create new peer review
    db_review = PeerReview(
        reviewer_id=current_user.id,
        employee_id=review.employee_id,
        liked=review.liked,
        is_anonymous=review.is_anonymous,
        comments=review.comments
    )
    
    db.add(db_review)
    
    # Add points for the reviewer
    points_transaction = PointsTransaction(
        user_id=current_user.id,
        amount=10,  # Award 10 points for submitting a peer review
        action="peer_review_submitted",
        description=f"Submitted peer review for employee {review.employee_id}"
    )
    db.add(points_transaction)
    
    # If liked, add points for the employee
    if review.liked:
        emp_points_transaction = PointsTransaction(
            user_id=review.employee_id,
            amount=5,  # Award 5 points for receiving a like
            action="peer_review_received_like",
            description=f"Received a like in peer review"
        )
        db.add(emp_points_transaction)
    
    db.commit()
    db.refresh(db_review)
    
    # Broadcast the like update via WebSocket
    # We use asyncio.create_task to avoid blocking the API response
    asyncio.create_task(broadcast_like_update(review.employee_id, review.liked))
    
    return db_review

@router.get("/me", response_model=List[PeerReviewInDB])
async def get_my_peer_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all peer reviews for the current user
    """
    reviews = db.query(PeerReview).filter(PeerReview.employee_id == current_user.id).all()
    
    # If review is anonymous, remove reviewer_id (except for admin/manager)
    for review in reviews:
        if review.is_anonymous and current_user.role not in ["admin", "manager"]:
            review.reviewer_id = None
    
    return reviews 