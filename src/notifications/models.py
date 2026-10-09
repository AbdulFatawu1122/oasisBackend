from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from src.entities.entities import NotificationType


class NotificationResponse(BaseModel):
    notification_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    reference_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int
