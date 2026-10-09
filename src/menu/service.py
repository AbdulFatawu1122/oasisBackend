from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status, UploadFile

from src.entities.entities import Category, Dish, DishMedia, MediaType
from src.storage.cloudflare_service import upload_file_to_r2, delete_file_from_r2
from . import models


# -----------------------------------------------------------------------------
# CATEGORIES
# -----------------------------------------------------------------------------
def get_all_categories(db: Session, active_only: bool = True) -> List[Category]:
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.order_by(Category.display_order.asc(), Category.name.asc()).all()


def create_category(payload: models.CategoryCreate, db: Session) -> Category:
    existing = db.query(Category).filter(
        func.lower(Category.slug) == payload.slug.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category slug '{payload.slug}' already exists."
        )

    cat = Category(
        slug=payload.slug.lower().strip(),
        name=payload.name.strip(),
        description=payload.description,
        icon_name=payload.icon_name,
        display_order=payload.display_order,
        is_active=payload.is_active
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# -----------------------------------------------------------------------------
# DISHES
# -----------------------------------------------------------------------------
def get_all_dishes(
    db: Session,
    category_slug: Optional[str] = None,
    search: Optional[str] = None,
    popular_only: bool = False,
    available_only: bool = True
) -> List[dict]:
    query = db.query(Dish).options(
        joinedload(Dish.category),
        joinedload(Dish.media)
    )

    if available_only:
        query = query.filter(Dish.is_available == True)

    if popular_only:
        query = query.filter(Dish.is_popular == True)

    if category_slug:
        query = query.join(Dish.category).filter(
            func.lower(Category.slug) == category_slug.lower().strip()
        )

    if search:
        kw = f"%{search.lower().strip()}%"
        query = query.filter(
            or_(
                func.lower(Dish.name).ilike(kw),
                func.lower(Dish.description).ilike(kw),
                func.lower(Dish.subtitle).ilike(kw)
            )
        )

    dishes = query.order_by(Dish.name.asc()).all()
    results = []
    for d in dishes:
        primary_media = next((m for m in d.media if m.is_primary), None)
        if not primary_media and d.media:
            primary_media = d.media[0]

        results.append({
            "dish_id": d.dish_id,
            "category_id": d.category_id,
            "category_name": d.category.name if d.category else None,
            "category_slug": d.category.slug if d.category else None,
            "name": d.name,
            "slug": d.slug,
            "subtitle": d.subtitle,
            "description": d.description,
            "price": d.price,
            "currency": d.currency,
            "calories": d.calories,
            "prep_time_minutes": d.prep_time_minutes,
            "tags": d.tags or [],
            "allergens": d.allergens or [],
            "wine_pairing": d.wine_pairing,
            "is_popular": d.is_popular,
            "is_available": d.is_available,
            "primary_image_url": primary_media.media_url if primary_media else None,
            "media": d.media
        })
    return results


def get_dish_by_id_or_slug(identifier: str, db: Session) -> dict:
    query = db.query(Dish).options(
        joinedload(Dish.category),
        joinedload(Dish.media)
    )
    try:
        val_uuid = UUID(identifier)
        dish = query.filter(Dish.dish_id == val_uuid).first()
    except ValueError:
        dish = query.filter(func.lower(Dish.slug) == identifier.lower().strip()).first()

    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found."
        )

    primary_media = next((m for m in dish.media if m.is_primary), None)
    if not primary_media and dish.media:
        primary_media = dish.media[0]

    return {
        "dish_id": dish.dish_id,
        "category_id": dish.category_id,
        "category_name": dish.category.name if dish.category else None,
        "category_slug": dish.category.slug if dish.category else None,
        "name": dish.name,
        "slug": dish.slug,
        "subtitle": dish.subtitle,
        "description": dish.description,
        "price": dish.price,
        "currency": dish.currency,
        "calories": dish.calories,
        "prep_time_minutes": dish.prep_time_minutes,
        "tags": dish.tags or [],
        "allergens": dish.allergens or [],
        "wine_pairing": dish.wine_pairing,
        "is_popular": dish.is_popular,
        "is_available": dish.is_available,
        "primary_image_url": primary_media.media_url if primary_media else None,
        "media": dish.media
    }


def create_dish(payload: models.DishCreate, db: Session) -> Dish:
    existing = db.query(Dish).filter(
        func.lower(Dish.slug) == payload.slug.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dish slug '{payload.slug}' already exists."
        )

    dish = Dish(
        category_id=payload.category_id,
        name=payload.name.strip(),
        slug=payload.slug.lower().strip(),
        subtitle=payload.subtitle.strip() if payload.subtitle else None,
        description=payload.description.strip(),
        price=payload.price,
        currency=payload.currency,
        calories=payload.calories,
        prep_time_minutes=payload.prep_time_minutes,
        tags=payload.tags,
        allergens=payload.allergens,
        wine_pairing=payload.wine_pairing,
        is_popular=payload.is_popular,
        is_available=payload.is_available
    )
    db.add(dish)
    db.commit()
    db.expire_all()
    db.refresh(dish)
    return dish


def update_dish(dish_id: UUID, payload: models.DishUpdate, db: Session) -> Dish:
    dish = db.query(Dish).filter(Dish.dish_id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(dish, field, val)

    db.commit()
    db.expire_all()
    db.refresh(dish)
    return dish


def delete_dish(dish_id: UUID, db: Session):
    dish = db.query(Dish).filter(Dish.dish_id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found."
        )
    db.delete(dish)
    db.commit()


# -----------------------------------------------------------------------------
# DISH MEDIA (Direct Cloudflare R2 Upload)
# -----------------------------------------------------------------------------
def upload_dish_media_asset(
    dish_id: UUID,
    file: UploadFile,
    is_primary: bool,
    display_order: int,
    db: Session
) -> DishMedia:
    dish = db.query(Dish).filter(Dish.dish_id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found."
        )

    media_id = uuid4()
    upload_res = upload_file_to_r2(file=file, folder="dishes", unique_id=media_id)

    # Detect media type (image or video)
    content_type = (file.content_type or "").lower()
    filename_lower = (file.filename or "").lower()
    is_video = (
        content_type.startswith("video/") or
        filename_lower.endswith((".mp4", ".mov", ".webm", ".mkv"))
    )
    media_type = MediaType.VIDEO if is_video else MediaType.IMAGE

    # If this is set to primary, clear existing primary flags for this dish
    if is_primary:
        db.query(DishMedia).filter(DishMedia.dish_id == dish_id).update({"is_primary": False})

    media = DishMedia(
        media_id=media_id,
        dish_id=dish_id,
        filename=file.filename or f"{media_id}",
        media_url=upload_res["url"],
        media_type=media_type,
        is_primary=is_primary,
        display_order=display_order
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def delete_dish_media_asset(dish_id: UUID, media_id: UUID, db: Session):
    media = db.query(DishMedia).filter(
        DishMedia.dish_id == dish_id,
        DishMedia.media_id == media_id
    ).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found."
        )

    # Delete from Cloudflare R2
    delete_file_from_r2(f"oasis/dishes/{media_id}")
    db.delete(media)
    db.commit()


def set_primary_dish_media(dish_id: UUID, media_id: UUID, db: Session) -> DishMedia:
    media = db.query(DishMedia).filter(
        DishMedia.dish_id == dish_id,
        DishMedia.media_id == media_id
    ).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found."
        )

    # Clear other primary flags for this dish
    db.query(DishMedia).filter(DishMedia.dish_id == dish_id).update({"is_primary": False})
    media.is_primary = True
    db.commit()
    db.expire_all()
    db.refresh(media)
    return media
