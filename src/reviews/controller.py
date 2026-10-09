from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, status, Depends, Query, HTTPException
from src.database.core import DbSession
from src.entities.entities import Admin
from src.admin_auth.service import RequireAdmin
from . import models, service

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews & Testimonials"]
)


@router.get("/featured", response_model=List[models.ReviewResponse])
def get_featured_reviews(db: DbSession):
    """Fetch verified featured reviews for the homepage testimonials section."""
    return service.get_featured_reviews(db=db)


@router.get("", response_model=List[models.ReviewResponse])
def list_all_reviews(
    db: DbSession,
    approved_only: Optional[bool] = Query(None),
    _: Admin = RequireAdmin
):
    """Fetch all reviews for moderation (Admin only)."""
    return service.get_all_reviews(db=db, approved_only=approved_only)


@router.post("/submit", response_model=models.ReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_review(payload: models.ReviewCreate, db: DbSession):
    """Submit a dining review or testimonial."""
    return service.create_customer_review(payload=payload, db=db)


@router.patch("/{review_id}", response_model=models.ReviewResponse)
def update_review(
    review_id: UUID,
    payload: models.ReviewUpdate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Approve or toggle featured status of a review (Admin only)."""
    try:
        return service.update_review(review_id=review_id, payload=payload, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: UUID,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Delete a review (Admin only)."""
    try:
        service.delete_review(review_id=review_id, db=db)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
