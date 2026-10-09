from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator
from src.entities.entities import MediaType


# -----------------------------------------------------------------------------
# CATEGORIES
# -----------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class CategoryResponse(BaseModel):
    category_id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: int
    is_active: bool

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# DISH MEDIA
# -----------------------------------------------------------------------------
class DishMediaResponse(BaseModel):
    media_id: UUID
    dish_id: UUID
    filename: str
    media_url: str
    media_type: MediaType
    is_primary: bool
    display_order: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# DISHES
# -----------------------------------------------------------------------------
class DishCreate(BaseModel):
    category_id: Optional[UUID] = None
    name: str
    slug: str
    subtitle: Optional[str] = None
    description: str
    price: Decimal
    currency: str = "USD"
    calories: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    tags: List[str] = []
    allergens: List[str] = []
    wine_pairing: Optional[str] = None
    is_popular: bool = False
    is_available: bool = True

    @field_validator("category_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class DishUpdate(BaseModel):
    category_id: Optional[UUID] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    calories: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    wine_pairing: Optional[str] = None
    is_popular: Optional[bool] = None
    is_available: Optional[bool] = None

    @field_validator("category_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class DishResponse(BaseModel):
    dish_id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    name: str
    slug: str
    subtitle: Optional[str] = None
    description: str
    price: Decimal
    currency: str
    calories: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    tags: List[str]
    allergens: List[str]
    wine_pairing: Optional[str] = None
    is_popular: bool
    is_available: bool
    primary_image_url: Optional[str] = None
    media: List[DishMediaResponse] = []

    class Config:
        from_attributes = True
