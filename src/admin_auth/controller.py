from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from src.database.core import DbSession
from src.entities.entities import Admin
from . import models, service
from .service import (
    CurrentAdmin,
    RequireSuperAdmin,
    RequireAdmin,
    authenticate_admin,
    create_admin_access_token
)

router = APIRouter(
    prefix="/admin-auth",
    tags=["Admin & Staff Auth"]
)

@router.post("/login", response_model=models.AdminTokenResponse)
def login_admin(payload: models.AdminLogin, db: DbSession):
    """
    Staff / Admin sign-in endpoint (JSON body for frontend apps).
    Delegates authentication and status checks to service.py.
    """
    admin = authenticate_admin(email=payload.email, password=payload.password, db=db)
    access_token = create_admin_access_token(
        admin_id=admin.admin_id,
        email=admin.email,
        role=admin.role.value
    )
    full_name = f"{admin.firstname} {admin.lastname}"
    if admin.other_name:
        full_name = f"{admin.firstname} {admin.other_name} {admin.lastname}"

    return models.AdminTokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=admin.role.value,
        admin_id=str(admin.admin_id),
        name=full_name
    )


@router.post("/token", response_model=models.AdminTokenResponse)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession
):
    """
    Standard OAuth2 password form endpoint (used by Swagger UI padlock and form clients).
    Accepts 'username' (email) and 'password' as form fields (no JSON quotes required).
    """
    admin = authenticate_admin(email=form_data.username, password=form_data.password, db=db)
    access_token = create_admin_access_token(
        admin_id=admin.admin_id,
        email=admin.email,
        role=admin.role.value
    )
    full_name = f"{admin.firstname} {admin.lastname}"
    if admin.other_name:
        full_name = f"{admin.firstname} {admin.other_name} {admin.lastname}"

    return models.AdminTokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=admin.role.value,
        admin_id=str(admin.admin_id),
        name=full_name
    )


@router.post("/new-admin", response_model=models.AdminResponse, status_code=status.HTTP_201_CREATED)
@router.post("/admin", response_model=models.AdminResponse, status_code=status.HTTP_201_CREATED)
def register_new_admin(
    payload: models.AdminCreate,
    request: Request,
    db: DbSession
):
    """
    Register a new admin.
    Delegates all business logic, bootstrap check, and persistence to service.register_admin.
    """
    return service.register_admin(db=db, admin=payload, request=request)


@router.get("/me", response_model=models.AdminResponse)
def get_my_admin_profile(current_admin: CurrentAdmin):
    """Returns the profile of the currently authenticated staff member."""
    return current_admin


@router.post("/staff", response_model=models.AdminResponse, status_code=status.HTTP_201_CREATED)
def create_staff_member(
    payload: models.AdminCreate,
    current_admin: CurrentAdmin,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """
    Create a new staff member (chef, waiter, cashier, host).
    Delegates creation and validation to service.register_admin.
    """
    return service.register_admin(db=db, admin=payload, creator_id=current_admin.admin_id)


@router.get("/staff", response_model=List[models.AdminResponse])
def list_staff_members(
    db: DbSession,
    _: Admin = RequireAdmin
):
    """List all staff accounts via service layer."""
    return service.list_staff_members(db=db)


@router.patch("/staff/{admin_id}/status", response_model=models.AdminResponse)
def update_staff_status(
    admin_id: UUID,
    payload: models.AdminStatusUpdate,
    db: DbSession,
    _: Admin = RequireAdmin
):
    """Update staff account status via service layer."""
    return service.update_staff_status(db=db, admin_id=admin_id, status=payload.status)


@router.delete("/staff/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff_member(
    admin_id: UUID,
    db: DbSession,
    _: Admin = RequireSuperAdmin
):
    """Delete a staff member permanently via service layer."""
    service.delete_staff_member(db=db, admin_id=admin_id)
    return None
