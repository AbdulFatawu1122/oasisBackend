from uuid import UUID
from typing import List
from fastapi import APIRouter, status, Depends, UploadFile, File, Query

from src.database.core import DbSession
from src.entities.entities import Admin
from src.admin_auth.service import RequireAdmin
from . import models, service

router = APIRouter(
    prefix="/seating-areas",
    tags=["Seating Areas"]
)


@router.get("", response_model=List[models.SeatingAreaResponse])
def list_seating_areas(
    db: DbSession,
    active_only: bool = Query(True, description="Filter active seating areas")
):
    """
    List restaurant seating areas (Open-Air Tropical Pavilion, VIP Dining Hall, Garden Terrace, etc.).
    Publicly accessible for table reservations.
    """
    return service.get_all_seating_areas(db=db, active_only=active_only)


@router.get("/{identifier}", response_model=models.SeatingAreaResponse)
def get_seating_area(identifier: str, db: DbSession):
    """Retrieve details for a specific seating zone by UUID or slug."""
    return service.get_seating_area_by_id_or_slug(identifier=identifier, db=db)


@router.post("", response_model=models.SeatingAreaResponse, status_code=status.HTTP_201_CREATED)
def create_seating_area(
    payload: models.SeatingAreaCreate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Add a new dining zone to the restaurant (Admin only)."""
    return service.create_seating_area(payload=payload, db=db)


@router.patch("/{area_id}", response_model=models.SeatingAreaResponse)
def update_seating_area(
    area_id: UUID,
    payload: models.SeatingAreaUpdate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Modify seating area details, capacity, tags, or status (Admin only)."""
    return service.update_seating_area(area_id=area_id, payload=payload, db=db)


@router.post("/{area_id}/media", status_code=status.HTTP_201_CREATED)
def upload_seating_area_photo_or_video(
    area_id: UUID,
    file: UploadFile = File(..., description="Ambiance photo or video of the zone"),
    db: DbSession = None,
    _: Admin = RequireAdmin
):
    """
    Upload an atmosphere photo or video directly to Cloudflare R2 for this dining zone.
    Guarded by Admin privileges.
    """
    return service.upload_seating_area_media(area_id=area_id, file=file, db=db)
