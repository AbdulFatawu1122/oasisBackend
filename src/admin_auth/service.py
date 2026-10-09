import os
from uuid import UUID, uuid4
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional, List
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from src.database.core import get_db, DbSession, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_MINUTES
from src.entities.entities import Admin, AdminRole, AdminStatus
from . import models

load_dotenv()

# OAuth2 scheme for Swagger UI & bearer authentication
oauth2_admin_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin-auth/token",
    scheme_name="AdminAuth"
)

# Password hashing configuration (argon2 + bcrypt fallback)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hashed(password: str) -> str:
    return pwd_context.hash(password)


def create_admin_access_token(
    admin_id: UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES)
    )
    payload = {
        "sub": email,
        "id": str(admin_id),
        "admin_id": str(admin_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_admin(email: str, password: str, db: Session) -> Admin:
    admin = db.query(Admin).filter(
        func.lower(Admin.email) == email.lower().strip()
    ).first()

    if not admin or not verify_password(password, admin.password_hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if admin.status == AdminStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your staff account is currently inactive. Please contact administration."
        )
    elif admin.status == AdminStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your staff account has been suspended. Please contact management."
        )

    # Record login timestamp
    admin.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)
    return admin


def get_current_admin(
    token: Annotated[str, Depends(oauth2_admin_scheme)],
    db: DbSession
) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id_str: str = payload.get("id") or payload.get("admin_id")
        if not admin_id_str:
            raise credentials_exception
        admin_id = UUID(admin_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )

    if admin.status != AdminStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active."
        )

    return admin


CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]


def require_access(required_privileges: Optional[List[str]] = None, allow_admin: bool = True):
    """
    Role & Privilege RBAC guard modeled on uniqkid_backend.
    - super_admin: Always permitted across all operations.
    - admin: Permitted if allow_admin=True.
    - user: Must possess at least one of the required_privileges.
    """
    def access_checker(current_admin: CurrentAdmin) -> Admin:
        if current_admin.status != AdminStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active."
            )

        # 1. Super Admins always have access
        if current_admin.role == AdminRole.SUPER_ADMIN:
            return current_admin

        # 2. General Admins have full access across modules
        if allow_admin and current_admin.role == AdminRole.ADMIN:
            return current_admin

        # 3. Operational 'user' role checks assigned privileges
        user_privileges = [str(p).lower() for p in (current_admin.privileges or [])]
        if required_privileges:
            matched = any(str(p).lower() in user_privileges for p in required_privileges)
            if matched:
                return current_admin

        req_str = ", ".join(required_privileges) if required_privileges else "Admin"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"PRIVILEGE_RESTRICTED: Your account does not have permission for this resource. Required privilege: {req_str}."
        )
    return access_checker


# Ready-to-use dependency aliases
RequireSuperAdmin   = Depends(require_access([], allow_admin=False))
RequireAdmin        = Depends(require_access([], allow_admin=True))
RequireChef         = Depends(require_access(["chef"]))
RequireWaiter       = Depends(require_access(["waiter"]))
RequireCashier      = Depends(require_access(["cashier"]))
RequireKitchenStaff = Depends(require_access(["kitchen_staff", "chef"]))


# =============================================================================
# ADMIN BUSINESS LOGIC & DATA OPERATIONS
# =============================================================================

def register_admin(
    db: Session,
    admin: models.AdminCreate,
    creator_id: Optional[UUID] = None,
    request: Optional[Request] = None
) -> Admin:
    """
    Registers a new admin/staff member.
    - If system has 0 admins, allows bootstrapping the initial super admin.
    - If admins exist, validates creator_id or Bearer token for Super Admin / Admin role.
    """
    total_admins = db.query(Admin).count()

    if total_admins > 0:
        # Resolve creator permissions
        if creator_id:
            creator_admin = db.query(Admin).filter(Admin.admin_id == creator_id).first()
            if not creator_admin or creator_admin.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Admin or Super Admin privilege required to create accounts."
                )
        elif request:
            auth_header = request.headers.get("Authorization") or request.headers.get("authorization") or ""
            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please provide a valid Bearer token."
                )
            token = auth_header.split(" ", 1)[1]
            creator_admin = get_current_admin(token=token, db=db)
            if creator_admin.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Admin or Super Admin privilege required to create accounts."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to register admins."
            )

    # Check for duplicate email
    existing = db.query(Admin).filter(
        func.lower(Admin.email) == admin.email.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # First admin is always super_admin if not specified
    role_to_assign = admin.role
    if total_admins == 0 and admin.role == AdminRole.USER:
        role_to_assign = AdminRole.SUPER_ADMIN

    hashed_password = get_password_hashed(admin.password)

    db_new_admin = Admin(
        admin_id=uuid4(),
        firstname=admin.firstname.strip(),
        lastname=admin.lastname.strip(),
        other_name=admin.other_name.strip() if admin.other_name else None,
        email=admin.email.lower().strip(),
        phone=admin.phone.strip() if admin.phone else None,
        role=role_to_assign,
        status=admin.status,
        privileges=[p.lower().strip() for p in admin.privileges],
        password_hashed=hashed_password
    )

    db.add(db_new_admin)
    db.commit()
    db.refresh(db_new_admin)
    return db_new_admin


def list_staff_members(db: Session) -> List[Admin]:
    """Retrieve all staff accounts ordered by creation date."""
    return db.query(Admin).order_by(Admin.created_at.desc()).all()


def update_staff_status(db: Session, admin_id: UUID, status: AdminStatus) -> Admin:
    """Update a staff member's account status (active, inactive, suspended)."""
    staff = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )

    staff.status = status
    db.commit()
    db.refresh(staff)
    return staff


def delete_staff_member(db: Session, admin_id: UUID) -> None:
    """Permanently delete a staff member."""
    staff = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )
    db.delete(staff)
    db.commit()
