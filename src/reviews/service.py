from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from src.entities.entities import Review
from . import models


def get_featured_reviews(db: Session) -> List[Review]:
    return db.query(Review).filter(
        Review.is_approved == True,
        Review.is_featured == True
    ).order_by(Review.created_at.desc()).limit(10).all()


def create_customer_review(payload: models.ReviewCreate, db: Session) -> Review:
    review = Review(
        author_name=payload.author_name.strip(),
        author_location=payload.author_location.strip() if payload.author_location else "Tamale, Ghana",
        avatar_url=payload.avatar_url,
        rating=payload.rating,
        quote=payload.quote.strip(),
        dish_id=payload.dish_id,
        is_approved=True,
        is_featured=False
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_all_reviews(db: Session, approved_only: bool = None) -> List[Review]:
    query = db.query(Review)
    if approved_only is not None:
        query = query.filter(Review.is_approved == approved_only)
    return query.order_by(Review.created_at.desc()).all()


def update_review(review_id: UUID, payload: models.ReviewUpdate, db: Session) -> Review:
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise ValueError("Review not found")
    if payload.is_approved is not None:
        review.is_approved = payload.is_approved
    if payload.is_featured is not None:
        review.is_featured = payload.is_featured
    db.commit()
    db.refresh(review)
    return review


def delete_review(review_id: UUID, db: Session):
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise ValueError("Review not found")
    db.delete(review)
    db.commit()
