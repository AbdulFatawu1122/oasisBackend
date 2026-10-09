from uuid import UUID, uuid4
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status, UploadFile

from src.entities.entities import SeatingArea
from src.storage.cloudflare_service import upload_file_to_r2
from . import models


def get_all_seating_areas(db: Session, active_only: bool = True) -> List[SeatingArea]:
    query = db.query(SeatingArea)
    if active_only:
        query = query.filter(SeatingArea.is_active == True)
    return query.order_by(SeatingArea.display_order.asc(), SeatingArea.name.asc()).all()


def get_seating_area_by_id_or_slug(identifier: str, db: Session) -> SeatingArea:
    try:
        val_uuid = UUID(identifier)
        area = db.query(SeatingArea).filter(SeatingArea.seating_area_id == val_uuid).first()
    except ValueError:
        area = db.query(SeatingArea).filter(
            func.lower(SeatingArea.slug) == identifier.lower().strip()
        ).first()

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seating area not found."
        )
    return area


def create_seating_area(payload: models.SeatingAreaCreate, db: Session) -> SeatingArea:
    existing = db.query(SeatingArea).filter(
        func.lower(SeatingArea.slug) == payload.slug.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Seating area with slug '{payload.slug}' already exists."
        )

    area = SeatingArea(
        name=payload.name.strip(),
        slug=payload.slug.lower().strip(),
        location=payload.location.strip() if payload.location else None,
        tags=[t.strip() for t in payload.tags],
        media=payload.media,
        capacity=payload.capacity,
        display_order=payload.display_order,
        is_active=payload.is_active
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def update_seating_area(area_id: UUID, payload: models.SeatingAreaUpdate, db: Session) -> SeatingArea:
    area = db.query(SeatingArea).filter(SeatingArea.seating_area_id == area_id).first()
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seating area not found."
        )

    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(area, field, val)

    db.commit()
    db.refresh(area)
    return area


def upload_seating_area_media(area_id: UUID, file: UploadFile, db: Session) -> dict:
    area = db.query(SeatingArea).filter(SeatingArea.seating_area_id == area_id).first()
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seating area not found."
        )

    unique_media_id = uuid4()
    res = upload_file_to_r2(file=file, folder="seating", unique_id=unique_media_id)

    # Append to media JSON list
    media_list = list(area.media or [])
    media_list.append(res["url"])
    area.media = media_list

    db.commit()
    db.refresh(area)
    return {"url": res["url"], "media": area.media}
