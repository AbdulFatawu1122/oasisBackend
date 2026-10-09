from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class CustomerRegister(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    delivery_address: Optional[str] = None


class CustomerLogin(BaseModel):
    email: EmailStr
    password: str


class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    name: str
    email: str


class CustomerResponse(BaseModel):
    customer_id: UUID
    firstname: str
    lastname: str
    email: str
    phone: Optional[str] = None
    delivery_address: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    delivery_address: Optional[str] = None
