from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, status, Depends, Query, HTTPException
from src.database.core import DbSession
from src.entities.entities import Admin, InquiryStatus
from src.admin_auth.service import RequireAdmin
from . import models, service

router = APIRouter(
    prefix="/contact",
    tags=["Contact"]
)


@router.post("/send", response_model=models.InquiryResponse, status_code=status.HTTP_201_CREATED)
def send_contact_inquiry(payload: models.InquiryCreate, db: DbSession):
    """Submit a public contact inquiry or feedback."""
    return service.create_inquiry(payload=payload, db=db)


@router.get("/inquiries", response_model=List[models.InquiryResponse])
def list_inquiries(
    db: DbSession,
    status: Optional[InquiryStatus] = Query(None),
    _: Admin = RequireAdmin
):
    """List customer contact inquiries (Admin only)."""
    return service.get_all_inquiries(db=db, status_filter=status)


@router.patch("/inquiries/{inquiry_id}/status", response_model=models.InquiryResponse)
def update_inquiry_status(
    inquiry_id: UUID,
    payload: models.InquiryStatusUpdate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Update status of customer inquiry (Admin only)."""
    try:
        return service.update_inquiry_status(inquiry_id=inquiry_id, status=payload.status, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/inquiries/{inquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inquiry(
    inquiry_id: UUID,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Delete a customer inquiry (Admin only)."""
    try:
        service.delete_inquiry(inquiry_id=inquiry_id, db=db)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
