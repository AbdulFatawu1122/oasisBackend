from uuid import UUID
from typing import List
from fastapi import APIRouter, status, Query

from src.database.core import DbSession
from . import models, service

router = APIRouter(
    prefix="/notifications",
    tags=["Admin Notifications"]
)


@router.get("", response_model=List[models.NotificationResponse])
def list_notifications(
    db: DbSession,
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    limit: int = Query(50, ge=1, le=200, description="Max notifications to retrieve")
):
    """Retrieve persistent operational alerts (orders, bookings, system notices)."""
    return service.get_notifications(db=db, unread_only=unread_only, limit=limit)


@router.get("/unread-count", response_model=models.UnreadCountResponse)
def get_unread_count(db: DbSession):
    """Get the active unread notification count for the topbar badge."""
    return {"unread_count": service.get_unread_count(db=db)}


@router.patch("/{notification_id}/read", response_model=models.NotificationResponse)
def mark_notification_read(notification_id: UUID, db: DbSession):
    """Mark an individual notification as read."""
    return service.mark_as_read(db=db, notification_id=notification_id)


@router.patch("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(db: DbSession):
    """Mark all active notifications as read."""
    marked = service.mark_all_as_read(db=db)
    return {"message": f"Marked {marked} notifications as read", "count": marked}
