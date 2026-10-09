from uuid import UUID
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from src.database.core import DbSession, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_MINUTES
from src.entities.entities import Customer

load_dotenv()

oauth2_customer_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="CustomerAuth"
)

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hashed(password: str) -> str:
    return pwd_context.hash(password)


def create_customer_access_token(
    customer_id: UUID,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES)
    )
    payload = {
        "sub": email,
        "id": str(customer_id),
        "customer_id": str(customer_id),
        "role": "customer",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_customer(email: str, password: str, db: Session) -> Customer:
    customer = db.query(Customer).filter(
        func.lower(Customer.email) == email.lower().strip()
    ).first()

    if not customer or not verify_password(password, customer.password_hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive. Please contact customer support."
        )

    customer.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(customer)
    return customer


def get_current_customer(
    token: Annotated[str, Depends(oauth2_customer_scheme)],
    db: DbSession
) -> Customer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate customer credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        customer_id_str: str = payload.get("id") or payload.get("customer_id")
        if not customer_id_str:
            raise credentials_exception
        customer_id = UUID(customer_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found or inactive."
        )

    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
