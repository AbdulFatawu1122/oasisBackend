import random
import string
from uuid import UUID, uuid4
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from datetime import datetime
from src.entities.entities import (
    Order, OrderItem, Dish, Promotion, OrderStatus, PaymentStatus, OrderType,
    Transaction, TransactionType, TransactionCategory, NotificationType
)
from src.notifications.service import create_notification
from src.websocket.manager import ws_manager
from . import models


def generate_order_number() -> str:
    suffix = "".join(random.choices(string.digits, k=5))
    return f"OAS-2026-{suffix}"


def create_order(
    payload: models.OrderCheckout,
    db: Session,
    customer_id: Optional[UUID] = None
) -> Order:
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item."
        )

    # 1. Fetch dishes and calculate subtotal
    subtotal = Decimal("0.00")
    order_items_data = []

    for item_input in payload.items:
        dish = db.query(Dish).filter(Dish.dish_id == item_input.dish_id).first()
        if not dish or not dish.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dish '{item_input.dish_id}' is unavailable or not found."
            )

        qty = max(1, item_input.quantity)
        line_total = Decimal(str(dish.price)) * Decimal(qty)
        subtotal += line_total

        order_items_data.append({
            "dish_id": dish.dish_id,
            "dish_name": dish.name,
            "unit_price": dish.price,
            "quantity": qty,
            "total_price": line_total,
            "special_requests": item_input.special_requests
        })

    # 2. Check and apply promotion code
    discount_amount = Decimal("0.00")
    promo_code_applied = None

    if payload.promo_code:
        code_str = payload.promo_code.upper().strip()
        promo = db.query(Promotion).filter(
            Promotion.code == code_str,
            Promotion.is_active == True
        ).first()

        if promo:
            if promo.min_order_amount and subtotal < promo.min_order_amount:
                pass  # below minimum order amount
            else:
                promo_code_applied = promo.code
                if promo.discount_type == "percentage":
                    discount_amount = (subtotal * Decimal(str(promo.discount_value))) / Decimal("100.00")
                else:
                    discount_amount = Decimal(str(promo.discount_value))
                
                # Increment usage counter
                promo.times_used += 1

    # 3. Delivery fee & Tax calculation
    delivery_fee = Decimal("5.00") if payload.order_type == OrderType.DELIVERY else Decimal("0.00")
    taxable_amount = max(Decimal("0.00"), subtotal - discount_amount)
    tax = (taxable_amount * Decimal("0.05")).quantize(Decimal("0.01"))  # 5% VAT/Sales tax
    total_amount = max(Decimal("0.00"), taxable_amount + tax + delivery_fee)

    # 4. Generate unique order number
    order_num = generate_order_number()
    while db.query(Order).filter(Order.order_number == order_num).first():
        order_num = generate_order_number()

    initial_payment_status = payload.payment_status or PaymentStatus.PENDING

    # 5. Create Order record
    order = Order(
        order_number=order_num,
        customer_id=customer_id,
        customer_name=payload.customer_name.strip() if payload.customer_name else None,
        customer_email=payload.customer_email.lower().strip() if payload.customer_email else None,
        customer_phone=payload.customer_phone.strip() if payload.customer_phone else None,
        order_type=payload.order_type,
        delivery_address=payload.delivery_address.strip() if payload.delivery_address else None,
        order_status=OrderStatus.PENDING,
        payment_status=initial_payment_status,
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        subtotal=subtotal,
        discount_amount=discount_amount,
        promo_code=promo_code_applied,
        tax=tax,
        delivery_fee=delivery_fee,
        total_amount=total_amount,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(order)
    db.flush()

    # 6. Create line items
    for oi in order_items_data:
        item_obj = OrderItem(
            order_id=order.order_id,
            dish_id=oi["dish_id"],
            dish_name=oi["dish_name"],
            unit_price=oi["unit_price"],
            quantity=oi["quantity"],
            total_price=oi["total_price"],
            special_requests=oi["special_requests"]
        )
        db.add(item_obj)

    # 7. Auto-record income transaction if already paid (e.g. POS cashier/terminal)
    if initial_payment_status == PaymentStatus.PAID:
        trx_count = db.query(Transaction).count() + 1
        trx = Transaction(
            reference_number=f"TRX-{datetime.now().strftime('%Y%m')}-{trx_count:05d}",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.FOOD_SALES,
            amount=total_amount,
            currency="GHS",
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
            order_id=order.order_id,
            description=f"POS Dining Sale #{order_num}",
        )
        db.add(trx)

    db.commit()
    db.refresh(order)

    # 8. Record persistent admin notification & broadcast via WebSocket
    try:
        customer_str = order.customer_name or "Walk-in Guest"
        notif_title = f"New Order #{order.order_number}"
        notif_msg = f"{customer_str} placed an order ({order.order_type.value}) for ₵{order.total_amount:.2f}"
        create_notification(
            db=db,
            notification_type=NotificationType.ORDER,
            title=notif_title,
            message=notif_msg,
            reference_id=str(order.order_id),
            data={
                "order_id": str(order.order_id),
                "order_number": order.order_number,
                "total_amount": float(order.total_amount),
                "order_type": order.order_type.value,
                "customer_name": order.customer_name,
            },
            broadcast=True
        )

        # Broadcast live order object for Dashboard and LiveOrders page
        ws_manager.broadcast_sync("NEW_ORDER", {
            "order_id": str(order.order_id),
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "order_type": order.order_type.value,
            "delivery_address": order.delivery_address,
            "order_status": order.order_status.value,
            "payment_status": order.payment_status.value,
            "payment_method": order.payment_method,
            "subtotal": float(order.subtotal),
            "discount_amount": float(order.discount_amount),
            "tax": float(order.tax),
            "total_amount": float(order.total_amount),
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "order_item_id": str(it.order_item_id),
                    "dish_name": it.dish_name,
                    "unit_price": float(it.unit_price),
                    "quantity": it.quantity,
                    "total_price": float(it.total_price),
                    "special_requests": it.special_requests,
                }
                for it in order.items
            ] if order.items else []
        })
    except Exception as e:
        pass

    return order


def get_order_by_number(order_number: str, db: Session) -> Order:
    order = db.query(Order).options(
        joinedload(Order.items)
    ).filter(
        Order.order_number == order_number.upper().strip()
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )
    return order


def list_orders(
    db: Session,
    status_filter: Optional[OrderStatus] = None,
    order_type_filter: Optional[OrderType] = None,
    limit: int = 50
) -> List[Order]:
    query = db.query(Order).options(joinedload(Order.items))
    if status_filter:
        query = query.filter(Order.order_status == status_filter)
    if order_type_filter:
        query = query.filter(Order.order_type == order_type_filter)

    return query.order_by(Order.created_at.desc()).limit(limit).all()


def update_order_status(
    order_id: UUID,
    payload: models.OrderStatusUpdate,
    admin_id: Optional[UUID],
    db: Session
) -> Order:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    order.order_status = payload.order_status
    if payload.payment_status:
        order.payment_status = payload.payment_status
        if payload.payment_status == PaymentStatus.PAID:
            existing_trx = db.query(Transaction).filter(Transaction.order_id == order.order_id).first()
            if not existing_trx:
                trx_count = db.query(Transaction).count() + 1
                trx = Transaction(
                    reference_number=f"TRX-{datetime.now().strftime('%Y%m')}-{trx_count:05d}",
                    transaction_type=TransactionType.INCOME,
                    category=TransactionCategory.FOOD_SALES,
                    amount=order.total_amount,
                    currency="GHS",
                    payment_method=order.payment_method,
                    payment_reference=order.payment_reference,
                    order_id=order.order_id,
                    recorded_by_admin_id=admin_id,
                    description=f"Order Payment #{order.order_number}",
                )
                db.add(trx)

    if admin_id:
        order.served_by_admin_id = admin_id

    db.commit()
    db.refresh(order)

    # Broadcast live status update to admin / kitchen dashboard
    try:
        ws_manager.broadcast_sync("ORDER_STATUS_UPDATED", {
            "order_id": str(order.order_id),
            "order_number": order.order_number,
            "order_status": order.order_status.value,
            "payment_status": order.payment_status.value,
        })
    except Exception:
        pass

    return order
