from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, status, Depends, Query

from src.database.core import DbSession
from src.entities.entities import Admin, OrderStatus, OrderType
from src.admin_auth.service import require_access
from . import models, service

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

# Staff guard: Waiter, Chef, Cashier, or Admin
RequireKitchenOrWaitstaff = Depends(require_access(["waiter", "chef", "cashier", "kitchen_staff"]))


@router.post("/checkout", response_model=models.OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout_order(payload: models.OrderCheckout, db: DbSession):
    """
    Public order placement endpoint (supports delivery, pickup, or dine-in QR orders).
    Customer details are nullable. Automatically calculates discounts and sales tax.
    """
    return service.create_order(payload=payload, db=db)


@router.get("/track/{order_number}", response_model=models.OrderResponse)
def track_order(order_number: str, db: DbSession):
    """Public real-time order tracking by order number (e.g. OAS-2026-XXXX)."""
    return service.get_order_by_number(order_number=order_number, db=db)


@router.get("", response_model=List[models.OrderResponse])
def list_orders_for_staff(
    db: DbSession,
    status: Optional[OrderStatus] = Query(None, description="Filter by status (pending, preparing, ready, etc.)"),
    order_type: Optional[OrderType] = Query(None, description="Filter by order type (delivery, pickup, dine_in)"),
    limit: int = Query(50, ge=1, le=200),
    _: Admin = RequireKitchenOrWaitstaff
):
    """Staff operational view for kitchen and floor orders."""
    return service.list_orders(
        db=db,
        status_filter=status,
        order_type_filter=order_type,
        limit=limit
    )


@router.patch("/{order_id}/status", response_model=models.OrderResponse)
def update_order_status(
    order_id: UUID,
    payload: models.OrderStatusUpdate,
    db: DbSession,
    staff: Admin = RequireKitchenOrWaitstaff
):
    """Update order kitchen/delivery status (PENDING -> CONFIRMED -> PREPARING -> READY -> DELIVERED)."""
    return service.update_order_status(
        order_id=order_id,
        payload=payload,
        admin_id=staff.admin_id,
        db=db
    )
