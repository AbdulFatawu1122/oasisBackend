from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    author_name: str
    author_location: Optional[str] = "Tamale, Ghana"
    avatar_url: Optional[str] = None
    rating: int = Field(5, ge=1, le=5)
    quote: str
    dish_id: Optional[UUID] = None


class ReviewUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_featured: Optional[bool] = None


class ReviewResponse(BaseModel):
    review_id: UUID
    author_name: str
    author_location: Optional[str] = None
    avatar_url: Optional[str] = None
    rating: int
    quote: str
    dish_id: Optional[UUID] = None
    is_featured: bool
    is_approved: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
