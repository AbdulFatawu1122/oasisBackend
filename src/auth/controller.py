from fastapi import APIRouter, status, HTTPException
from sqlalchemy import func

from src.database.core import DbSession
from src.entities.entities import Customer
from . import models, service
from .service import (
    CurrentCustomer,
    authenticate_customer,
    create_customer_access_token,
    get_password_hashed
)

router = APIRouter(
    prefix="/auth",
    tags=["Customer Auth"]
)


@router.post("/register", response_model=models.CustomerTokenResponse, status_code=status.HTTP_201_CREATED)
def register_customer(payload: models.CustomerRegister, db: DbSession):
    """Register a new customer account."""
    existing = db.query(Customer).filter(
        func.lower(Customer.email) == payload.email.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    new_customer = Customer(
        firstname=payload.firstname.strip(),
        lastname=payload.lastname.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip() if payload.phone else None,
        delivery_address=payload.delivery_address.strip() if payload.delivery_address else None,
        password_hashed=get_password_hashed(payload.password),
        is_active=True
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    token = create_customer_access_token(
        customer_id=new_customer.customer_id,
        email=new_customer.email
    )
    return models.CustomerTokenResponse(
        access_token=token,
        token_type="bearer",
        customer_id=str(new_customer.customer_id),
        name=f"{new_customer.firstname} {new_customer.lastname}",
        email=new_customer.email
    )


@router.post("/login", response_model=models.CustomerTokenResponse)
def login_customer(payload: models.CustomerLogin, db: DbSession):
    """Customer sign-in."""
    customer = authenticate_customer(email=payload.email, password=payload.password, db=db)
    token = create_customer_access_token(
        customer_id=customer.customer_id,
        email=customer.email
    )
    return models.CustomerTokenResponse(
        access_token=token,
        token_type="bearer",
        customer_id=str(customer.customer_id),
        name=f"{customer.firstname} {customer.lastname}",
        email=customer.email
    )


@router.get("/me", response_model=models.CustomerResponse)
def get_customer_profile(current_customer: CurrentCustomer):
    """Returns the profile of the current authenticated customer."""
    return current_customer


@router.patch("/profile", response_model=models.CustomerResponse)
def update_customer_profile(
    payload: models.CustomerUpdate,
    current_customer: CurrentCustomer,
    db: DbSession
):
    """Update profile details (name, phone, delivery address)."""
    if payload.firstname is not None:
        current_customer.firstname = payload.firstname.strip()
    if payload.lastname is not None:
        current_customer.lastname = payload.lastname.strip()
    if payload.phone is not None:
        current_customer.phone = payload.phone.strip()
    if payload.delivery_address is not None:
        current_customer.delivery_address = payload.delivery_address.strip()

    db.commit()
    db.refresh(current_customer)
    return current_customer
