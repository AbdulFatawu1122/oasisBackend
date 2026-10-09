from uuid import UUID
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from src.entities.entities import ReservationStatus


class ReservationCreate(BaseModel):
    seating_area_id: Optional[UUID] = None
    name: str
    email: EmailStr
    phone: str
    reservation_date: date
    reservation_time: time
    guests_count: int = 2
    special_requests: Optional[str] = None


class ReservationResponse(BaseModel):
    reservation_id: UUID
    reference_code: str
    customer_id: Optional[UUID] = None
    assigned_admin_id: Optional[UUID] = None
    seating_area_id: Optional[UUID] = None
    seating_area_name: Optional[str] = None
    name: str
    email: str
    phone: str
    reservation_date: date
    reservation_time: time
    guests_count: int
    special_requests: Optional[str] = None
    status: ReservationStatus
    table_number: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservationStatusUpdate(BaseModel):
    status: ReservationStatus
    table_number: Optional[str] = None
