from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class SeatingAreaCreate(BaseModel):
    name: str
    slug: str
    location: Optional[str] = None
    tags: List[str] = []
    media: List[str] = []
    capacity: Optional[int] = None
    display_order: int = 0
    is_active: bool = True


class SeatingAreaUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    media: Optional[List[str]] = None
    capacity: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class SeatingAreaResponse(BaseModel):
    seating_area_id: UUID
    name: str
    slug: str
    location: Optional[str] = None
    tags: List[str]
    media: List[str]
    capacity: Optional[int] = None
    display_order: int
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
