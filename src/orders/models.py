from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from src.entities.entities import OrderType, OrderStatus, PaymentStatus


class OrderItemInput(BaseModel):
    dish_id: UUID
    quantity: int = 1
    special_requests: Optional[str] = None


class OrderCheckout(BaseModel):
    # Customer details strictly optional for walk-in QR table orders
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    order_type: OrderType = OrderType.DELIVERY
    delivery_address: Optional[str] = None
    payment_method: str = "card"
    payment_reference: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None
    promo_code: Optional[str] = None
    notes: Optional[str] = None
    items: List[OrderItemInput]


class OrderItemResponse(BaseModel):
    order_item_id: UUID
    dish_id: UUID
    dish_name: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    special_requests: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    order_id: UUID
    order_number: str
    customer_id: Optional[UUID] = None
    served_by_admin_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    order_type: OrderType
    delivery_address: Optional[str] = None
    order_status: OrderStatus
    payment_status: PaymentStatus
    payment_method: str
    payment_reference: Optional[str] = None
    subtotal: Decimal
    discount_amount: Decimal
    promo_code: Optional[str] = None
    tax: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    order_status: OrderStatus
    payment_status: Optional[PaymentStatus] = None
