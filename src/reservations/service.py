import random
import string
from uuid import UUID
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from src.entities.entities import Reservation, SeatingArea, ReservationStatus, NotificationType
from src.notifications.service import create_notification
from src.websocket.manager import ws_manager
from . import models


def generate_reference_code() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=5))
    return f"OAS-RES-{suffix}"


def create_reservation(
    payload: models.ReservationCreate,
    db: Session,
    customer_id: Optional[UUID] = None
) -> dict:
    # Verify seating area if provided
    seating_name = None
    if payload.seating_area_id:
        area = db.query(SeatingArea).filter(SeatingArea.seating_area_id == payload.seating_area_id).first()
        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected seating area does not exist."
            )
        seating_name = area.name

    # Generate unique reference code
    ref_code = generate_reference_code()
    while db.query(Reservation).filter(Reservation.reference_code == ref_code).first():
        ref_code = generate_reference_code()

    reservation = Reservation(
        reference_code=ref_code,
        customer_id=customer_id,
        seating_area_id=payload.seating_area_id,
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip(),
        reservation_date=payload.reservation_date,
        reservation_time=payload.reservation_time,
        guests_count=payload.guests_count,
        special_requests=payload.special_requests.strip() if payload.special_requests else None,
        status=ReservationStatus.CONFIRMED
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    # Record persistent admin notification & broadcast via WebSocket
    try:
        area_str = seating_name or "Main Dining Room"
        notif_title = f"New Table Reservation ({reservation.guests_count} Guests)"
        notif_msg = f"{reservation.name} booked for {reservation.reservation_date} at {reservation.reservation_time} ({area_str})"
        create_notification(
            db=db,
            notification_type=NotificationType.RESERVATION,
            title=notif_title,
            message=notif_msg,
            reference_id=str(reservation.reservation_id),
            data={
                "reservation_id": str(reservation.reservation_id),
                "reference_code": reservation.reference_code,
                "name": reservation.name,
                "phone": reservation.phone,
                "guests_count": reservation.guests_count,
                "reservation_date": str(reservation.reservation_date),
                "reservation_time": str(reservation.reservation_time),
                "seating_name": area_str,
            },
            broadcast=True
        )

        ws_manager.broadcast_sync("NEW_RESERVATION", {
            "reservation_id": str(reservation.reservation_id),
            "reference_code": reservation.reference_code,
            "name": reservation.name,
            "email": reservation.email,
            "phone": reservation.phone,
            "guests_count": reservation.guests_count,
            "reservation_date": str(reservation.reservation_date),
            "reservation_time": str(reservation.reservation_time),
            "seating_area_name": area_str,
            "special_requests": reservation.special_requests,
            "status": reservation.status.value,
            "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
        })
    except Exception:
        pass

    return {
        "reservation_id": reservation.reservation_id,
        "reference_code": reservation.reference_code,
        "customer_id": reservation.customer_id,
        "assigned_admin_id": reservation.assigned_admin_id,
        "seating_area_id": reservation.seating_area_id,
        "seating_area_name": seating_name,
        "name": reservation.name,
        "email": reservation.email,
        "phone": reservation.phone,
        "reservation_date": reservation.reservation_date,
        "reservation_time": reservation.reservation_time,
        "guests_count": reservation.guests_count,
        "special_requests": reservation.special_requests,
        "status": reservation.status,
        "table_number": reservation.table_number,
        "created_at": reservation.created_at
    }


def get_reservation_by_code(code: str, db: Session) -> dict:
    res = db.query(Reservation).options(
        joinedload(Reservation.seating_area)
    ).filter(
        Reservation.reference_code == code.upper().strip()
    ).first()

    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found with this reference code."
        )

    return {
        "reservation_id": res.reservation_id,
        "reference_code": res.reference_code,
        "customer_id": res.customer_id,
        "assigned_admin_id": res.assigned_admin_id,
        "seating_area_id": res.seating_area_id,
        "seating_area_name": res.seating_area.name if res.seating_area else None,
        "name": res.name,
        "email": res.email,
        "phone": res.phone,
        "reservation_date": res.reservation_date,
        "reservation_time": res.reservation_time,
        "guests_count": res.guests_count,
        "special_requests": res.special_requests,
        "status": res.status,
        "table_number": res.table_number,
        "created_at": res.created_at
    }


def list_reservations(
    db: Session,
    booking_date: Optional[date] = None,
    status_filter: Optional[ReservationStatus] = None,
    seating_area_id: Optional[UUID] = None
) -> List[dict]:
    query = db.query(Reservation).options(joinedload(Reservation.seating_area))
    if booking_date:
        query = query.filter(Reservation.reservation_date == booking_date)
    if status_filter:
        query = query.filter(Reservation.status == status_filter)
    if seating_area_id:
        query = query.filter(Reservation.seating_area_id == seating_area_id)

    reservations = query.order_by(Reservation.reservation_date.desc(), Reservation.reservation_time.asc()).all()
    results = []
    for r in reservations:
        results.append({
            "reservation_id": r.reservation_id,
            "reference_code": r.reference_code,
            "customer_id": r.customer_id,
            "assigned_admin_id": r.assigned_admin_id,
            "seating_area_id": r.seating_area_id,
            "seating_area_name": r.seating_area.name if r.seating_area else None,
            "name": r.name,
            "email": r.email,
            "phone": r.phone,
            "reservation_date": r.reservation_date,
            "reservation_time": r.reservation_time,
            "guests_count": r.guests_count,
            "special_requests": r.special_requests,
            "status": r.status,
            "table_number": r.table_number,
            "created_at": r.created_at
        })
    return results


def update_reservation_status(
    reservation_id: UUID,
    payload: models.ReservationStatusUpdate,
    admin_id: Optional[UUID],
    db: Session
) -> Reservation:
    res = db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found."
        )

    res.status = payload.status
    if payload.table_number is not None:
        res.table_number = payload.table_number.strip()
    if admin_id:
        res.assigned_admin_id = admin_id

    db.commit()
    db.refresh(res)
    return res
