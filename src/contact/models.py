from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from src.entities.entities import InquiryStatus


class InquiryCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str


class InquiryStatusUpdate(BaseModel):
    status: InquiryStatus


class InquiryResponse(BaseModel):
    inquiry_id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str
    status: InquiryStatus
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
