from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, status, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from src.database.core import DbSession
from src.entities.entities import Admin
from src.admin_auth.service import RequireAdmin
from . import models, service

router = APIRouter(
    prefix="/menu",
    tags=["Menu Catalog"]
)


# -----------------------------------------------------------------------------
# CATEGORIES ENDPOINTS
# -----------------------------------------------------------------------------
@router.get("/categories", response_model=List[models.CategoryResponse])
def list_categories(
    db: DbSession,
    active_only: bool = Query(True, description="Filter only active categories")
):
    """Retrieve all menu categories (Fast Food, Pizza, Beverages, etc.)."""
    return service.get_all_categories(db=db, active_only=active_only)


@router.post("/categories", response_model=models.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: models.CategoryCreate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Create a new menu category (Admin only)."""
    return service.create_category(payload=payload, db=db)


# -----------------------------------------------------------------------------
# DISHES ENDPOINTS
# -----------------------------------------------------------------------------
@router.get("/dishes", response_model=List[models.DishResponse])
def list_dishes(
    db: DbSession,
    category: Optional[str] = Query(None, description="Filter by category slug"),
    search: Optional[str] = Query(None, description="Search keyword in name/description"),
    popular: bool = Query(False, description="Filter popular featured dishes"),
    available_only: bool = Query(True, description="Filter in-stock dishes")
):
    """
    Public menu search and filter endpoint.
    Includes Cloudflare CDN media URLs (photos and videos).
    """
    return service.get_all_dishes(
        db=db,
        category_slug=category,
        search=search,
        popular_only=popular,
        available_only=available_only
    )


@router.get("/dishes/{identifier}", response_model=models.DishResponse)
def get_dish_details(identifier: str, db: DbSession):
    """Fetch dish details by UUID or slug."""
    return service.get_dish_by_id_or_slug(identifier=identifier, db=db)


@router.post("/dishes", response_model=models.DishResponse, status_code=status.HTTP_201_CREATED)
def create_dish(
    payload: models.DishCreate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Create a new dish (Admin only)."""
    dish = service.create_dish(payload=payload, db=db)
    return service.get_dish_by_id_or_slug(identifier=str(dish.dish_id), db=db)


@router.patch("/dishes/{dish_id}", response_model=models.DishResponse)
def update_dish(
    dish_id: UUID,
    payload: models.DishUpdate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Update dish details, pricing, tags, or availability (Admin only)."""
    service.update_dish(dish_id=dish_id, payload=payload, db=db)
    return service.get_dish_by_id_or_slug(identifier=str(dish_id), db=db)


@router.delete("/dishes/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(
    dish_id: UUID,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Delete a dish from the catalog (Admin only)."""
    service.delete_dish(dish_id=dish_id, db=db)
    return None


# -----------------------------------------------------------------------------
# MEDIA UPLOADS (Cloudflare R2 Direct Uploads)
# -----------------------------------------------------------------------------
@router.post("/dishes/{dish_id}/media", response_model=models.DishMediaResponse, status_code=status.HTTP_201_CREATED)
def upload_media_for_dish(
    dish_id: UUID,
    file: UploadFile = File(..., description="High-resolution image or video"),
    is_primary: bool = Form(False, description="Set as main thumbnail"),
    display_order: int = Form(0, description="Sort order in gallery"),
    db: DbSession = None,
    _: Admin = RequireAdmin
):
    """
    Upload a high-resolution photo or plating video directly to Cloudflare R2 for a dish.
    Guarded by Admin privileges.
    """
    return service.upload_dish_media_asset(
        dish_id=dish_id,
        file=file,
        is_primary=is_primary,
        display_order=display_order,
        db=db
    )


@router.delete("/dishes/{dish_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_from_dish(
    dish_id: UUID,
    media_id: UUID,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Remove a media asset from a dish and delete from Cloudflare R2."""
    service.delete_dish_media_asset(dish_id=dish_id, media_id=media_id, db=db)
    return None


@router.patch("/dishes/{dish_id}/media/{media_id}/primary", response_model=models.DishMediaResponse)
def set_primary_dish_media(
    dish_id: UUID,
    media_id: UUID,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Set a specific media asset as the primary display asset for a dish."""
    return service.set_primary_dish_media(dish_id=dish_id, media_id=media_id, db=db)
