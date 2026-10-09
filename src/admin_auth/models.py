from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from src.entities.entities import AdminRole, AdminStatus


class TokenData(BaseModel):
    id: str | None = None
    email: str | None = None
    role: str | None = None
    admin_id: str | None = None

    def get_uuid(self) -> UUID | None:
        val = self.id or self.admin_id
        if val:
            return UUID(val)
        return None


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    admin_id: str
    name: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminCreate(BaseModel):
    firstname: str
    lastname: str
    other_name: Optional[str] = None
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: AdminRole = AdminRole.USER
    status: AdminStatus = AdminStatus.ACTIVE
    privileges: List[str] = []


class AdminResponse(BaseModel):
    admin_id: UUID
    firstname: str
    lastname: str
    other_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    role: AdminRole
    status: AdminStatus
    privileges: List[str]
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminStatusUpdate(BaseModel):
    status: AdminStatus
