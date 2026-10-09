from uuid import UUID
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.entities.entities import AdminNotification, NotificationType
from src.websocket.manager import ws_manager


def create_notification(
    db: Session,
    notification_type: NotificationType,
    title: str,
    message: str,
    reference_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    broadcast: bool = True
) -> AdminNotification:
    """
    Persists an admin notification in the database and broadcasts it in real time via WebSocket.
    """
    notif = AdminNotification(
        notification_type=notification_type,
        title=title,
        message=message,
        reference_id=str(reference_id) if reference_id else None,
        data=data or {},
        is_read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    if broadcast:
        payload = {
            "notification_id": str(notif.notification_id),
            "notification_type": notif.notification_type.value,
            "title": notif.title,
            "message": notif.message,
            "reference_id": notif.reference_id,
            "data": notif.data,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat() if notif.created_at else None
        }
        ws_manager.broadcast_sync("NEW_NOTIFICATION", payload)

    return notif


def get_notifications(
    db: Session,
    unread_only: bool = False,
    limit: int = 50
) -> List[AdminNotification]:
    query = db.query(AdminNotification).order_by(AdminNotification.created_at.desc())
    if unread_only:
        query = query.filter(AdminNotification.is_read.is_(False))
    return query.limit(limit).all()


def mark_as_read(db: Session, notification_id: UUID) -> AdminNotification:
    notif = db.query(AdminNotification).filter(AdminNotification.notification_id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_as_read(db: Session) -> int:
    count = db.query(AdminNotification).filter(AdminNotification.is_read.is_(False)).update(
        {"is_read": True},
        synchronize_session="fetch"
    )
    db.commit()
    return count


def get_unread_count(db: Session) -> int:
    return db.query(AdminNotification).filter(AdminNotification.is_read.is_(False)).count()
