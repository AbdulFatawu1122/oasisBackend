from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from src.entities.entities import ContactInquiry, InquiryStatus
from . import models


def create_inquiry(payload: models.InquiryCreate, db: Session) -> ContactInquiry:
    inquiry = ContactInquiry(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip() if payload.phone else None,
        subject=payload.subject.strip() if payload.subject else None,
        message=payload.message.strip(),
        status=InquiryStatus.UNREAD
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry


def get_all_inquiries(db: Session, status_filter: InquiryStatus = None) -> List[ContactInquiry]:
    query = db.query(ContactInquiry)
    if status_filter:
        query = query.filter(ContactInquiry.status == status_filter)
    return query.order_by(ContactInquiry.created_at.desc()).all()


def update_inquiry_status(inquiry_id: UUID, status: InquiryStatus, db: Session) -> ContactInquiry:
    inquiry = db.query(ContactInquiry).filter(ContactInquiry.inquiry_id == inquiry_id).first()
    if not inquiry:
        raise ValueError("Inquiry not found")
    inquiry.status = status
    db.commit()
    db.refresh(inquiry)
    return inquiry


def delete_inquiry(inquiry_id: UUID, db: Session):
    inquiry = db.query(ContactInquiry).filter(ContactInquiry.inquiry_id == inquiry_id).first()
    if not inquiry:
        raise ValueError("Inquiry not found")
    db.delete(inquiry)
    db.commit()
