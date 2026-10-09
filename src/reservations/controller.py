from uuid import UUID
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, status, Depends, Query

from src.database.core import DbSession
from src.entities.entities import Admin, ReservationStatus
from src.admin_auth.service import require_access
from . import models, service

router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)

# Staff guard: Host, Waiter, Manager, or Admin
RequireReservationStaff = Depends(require_access(["waiter", "host", "cashier"]))


@router.post("/book", response_model=models.ReservationResponse, status_code=status.HTTP_201_CREATED)
def book_table(payload: models.ReservationCreate, db: DbSession):
    """
    Public guest dining reservation booking.
    Generates a unique tracking reference code (e.g. OAS-RES-XXXX).
    """
    return service.create_reservation(payload=payload, db=db)


@router.get("/verify/{reference_code}", response_model=models.ReservationResponse)
def verify_reservation(reference_code: str, db: DbSession):
    """Verify or check reservation details via reference code."""
    return service.get_reservation_by_code(code=reference_code, db=db)


@router.get("", response_model=List[models.ReservationResponse])
def list_reservations_for_staff(
    db: DbSession,
    booking_date: Optional[date] = Query(None, description="Filter bookings by date"),
    status: Optional[ReservationStatus] = Query(None, description="Filter by status"),
    seating_area_id: Optional[UUID] = Query(None, description="Filter by seating area"),
    _: Admin = RequireReservationStaff
):
    """Staff dashboard view for dining reservations (Waiters, Hosts, Managers)."""
    return service.list_reservations(
        db=db,
        booking_date=booking_date,
        status_filter=status,
        seating_area_id=seating_area_id
    )


@router.patch("/{reservation_id}/status")
def update_reservation_status(
    reservation_id: UUID,
    payload: models.ReservationStatusUpdate,
    db: DbSession,
    staff: Admin = RequireReservationStaff
):
    """Update reservation state (CONFIRMED -> SEATED -> COMPLETED / CANCELLED)."""
    service.update_reservation_status(
        reservation_id=reservation_id,
        payload=payload,
        admin_id=staff.admin_id,
        db=db
    )
    return {"message": "Reservation status updated successfully."}
