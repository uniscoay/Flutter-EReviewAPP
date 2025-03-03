from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict
from pydantic import BaseModel

from ..db import get_db
from ..models.user import User, UserOut
from ..models.points import PointsTransaction, PointsTransactionInDB, Badge, UserBadge, BadgeInDB
from .auth import get_current_active_user

router = APIRouter()

class UserPoints(BaseModel):
    user: UserOut
    total_points: int

class LeaderboardEntry(BaseModel):
    rank: int
    user: UserOut
    points: int

class UserPointsDetail(BaseModel):
    user: UserOut
    total_points: int
    badges: List[BadgeInDB]
    transactions: List[PointsTransactionInDB]

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = 10
):
    """
    Get the points leaderboard
    """
    # Get sum of points for each user
    points_by_user = db.query(
        User, 
        func.sum(PointsTransaction.amount).label("total_points")
    ).join(
        PointsTransaction, 
        User.id == PointsTransaction.user_id
    ).group_by(
        User.id
    ).order_by(
        desc("total_points")
    ).limit(limit).all()
    
    # Format results with rank
    result = []
    for rank, (user, points) in enumerate(points_by_user, 1):
        result.append(LeaderboardEntry(
            rank=rank,
            user=user,
            points=points
        ))
    
    return result

@router.get("/{user_id}", response_model=UserPointsDetail)
async def get_user_points(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a user's points and badges
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's total points
    total_points = db.query(
        func.sum(PointsTransaction.amount)
    ).filter(
        PointsTransaction.user_id == user_id
    ).scalar() or 0
    
    # Get user's badges
    badges = db.query(Badge).join(
        UserBadge, 
        Badge.id == UserBadge.badge_id
    ).filter(
        UserBadge.user_id == user_id
    ).all()
    
    # Get user's point transactions
    transactions = db.query(PointsTransaction).filter(
        PointsTransaction.user_id == user_id
    ).order_by(
        PointsTransaction.created_at.desc()
    ).all()
    
    return UserPointsDetail(
        user=user,
        total_points=total_points,
        badges=badges,
        transactions=transactions
    ) 