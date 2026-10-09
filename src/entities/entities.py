import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Integer, Numeric, Boolean,
    DateTime, Date, Time, Enum, ForeignKey, JSON
)
from sqlalchemy import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.core import Base

# =============================================================================
# GLOBAL ENUMS
# =============================================================================

class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"  # Full platform control (system settings, financial audit, staff creation)
    ADMIN = "admin"              # Restaurant managerial control (menu, pricing, reports, seating config)
    USER = "user"                # Operational restaurant staff (waiters, chefs, kitchen, cashiers)


class AdminStatus(str, enum.Enum):
    ACTIVE = "active"            # Account operational and permitted to log in
    INACTIVE = "inactive"        # Deactivated (e.g., on leave, seasonal pause)
    SUSPENDED = "suspended"      # Locked out by administration


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class OrderType(str, enum.Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"
    DINE_IN = "dine_in"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class InquiryStatus(str, enum.Enum):
    UNREAD = "unread"
    RESPONDED = "responded"
    ARCHIVED = "archived"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    PAYOUT = "payout"


class TransactionCategory(str, enum.Enum):
    FOOD_SALES = "food_sales"
    BEVERAGE_SALES = "beverage_sales"
    CATERING_SALES = "catering_sales"
    KITCHEN_PROCUREMENT = "kitchen_procurement"
    STAFF_WAGES = "staff_wages"
    UTILITIES = "utilities"
    MAINTENANCE = "maintenance"
    PACKAGING = "packaging"
    MARKETING = "marketing"
    OTHER = "other"


class ExpenseCategory(str, enum.Enum):
    KITCHEN_INGREDIENTS = "kitchen_ingredients"
    BEVERAGES_STOCK = "beverages_stock"
    UTILITIES = "utilities"
    STAFF_WAGES = "staff_wages"
    PACKAGING_SUPPLIES = "packaging_supplies"
    MAINTENANCE_REPAIRS = "maintenance_repairs"
    MARKETING = "marketing"
    OTHER = "other"


class NotificationType(str, enum.Enum):
    ORDER = "order"
    RESERVATION = "reservation"
    SYSTEM = "system"


# =============================================================================
# ENTITIES
# =============================================================================

class Admin(Base):
    """
    Internal restaurant staff & leadership (Super Admins, Admins, Waiters, Chefs, Cashiers).
    """
    __tablename__ = "admins"

    admin_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hashed = Column(String, nullable=False)
    firstname = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    other_name = Column(String(100), nullable=True)
    phone = Column(String(50), index=True, nullable=True)
    role = Column(Enum(AdminRole), default=AdminRole.USER, nullable=False, index=True)
    status = Column(Enum(AdminStatus), default=AdminStatus.ACTIVE, nullable=False, index=True)
    privileges = Column(JSON, default=list, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    processed_orders = relationship("Order", back_populates="served_by_admin")
    assigned_reservations = relationship("Reservation", back_populates="assigned_admin")
    recorded_expenses = relationship("Expense", back_populates="recorded_by")
    recorded_transactions = relationship("Transaction", back_populates="recorded_by")


class Customer(Base):
    """
    Public restaurant consumer diner accounts.
    """
    __tablename__ = "customers"

    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hashed = Column(String, nullable=False)
    firstname = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    phone = Column(String(50), index=True, nullable=True)
    delivery_address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer")
    reservations = relationship("Reservation", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")


class Category(Base):
    """
    Menu categories (Fast Food, Pizza, Drinks, Traditional, etc.).
    """
    __tablename__ = "categories"

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon_name = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dishes = relationship("Dish", back_populates="category")


class Dish(Base):
    """
    Food items offered by Oasis Restaurant.
    """
    __tablename__ = "dishes"

    dish_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id", ondelete="SET NULL"), index=True, nullable=True)
    name = Column(String(150), index=True, nullable=False)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    subtitle = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    calories = Column(Integer, nullable=True)
    prep_time_minutes = Column(Integer, nullable=True)
    tags = Column(JSON, default=list)
    allergens = Column(JSON, default=list)
    wine_pairing = Column(String(150), nullable=True)
    is_popular = Column(Boolean, default=False, index=True)
    is_available = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="dishes")
    media = relationship("DishMedia", back_populates="dish", cascade="all, delete-orphan", order_by="DishMedia.display_order")
    order_items = relationship("OrderItem", back_populates="dish")
    reviews = relationship("Review", back_populates="dish")


class DishMedia(Base):
    """
    Dedicated media table supporting multiple images and videos per dish.
    """
    __tablename__ = "dish_media"

    media_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id = Column(UUID(as_uuid=True), ForeignKey("dishes.dish_id", ondelete="CASCADE"), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    media_url = Column(String(500), nullable=False)
    media_type = Column(Enum(MediaType), default=MediaType.IMAGE, nullable=False)
    is_primary = Column(Boolean, default=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dish = relationship("Dish", back_populates="media")


class SeatingArea(Base):
    """
    Restaurant dining sections configured dynamically by the restaurant
    (e.g., Open-Air Tropical Pavilion, Main Dining Hall, VIP Lounge, Garden Terrace).
    """
    __tablename__ = "seating_areas"

    seating_area_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    location = Column(String(150), nullable=True)
    tags = Column(JSON, default=list)
    media = Column(JSON, default=list)
    capacity = Column(Integer, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reservations = relationship("Reservation", back_populates="seating_area")


class Order(Base):
    """
    Customer orders supporting delivery, pickup, and walk-in/QR dine-in.
    """
    __tablename__ = "orders"

    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(30), unique=True, index=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="SET NULL"), index=True, nullable=True)
    served_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id", ondelete="SET NULL"), index=True, nullable=True)
    customer_name = Column(String(150), nullable=True)
    customer_email = Column(String(255), index=True, nullable=True)
    customer_phone = Column(String(50), nullable=True)
    order_type = Column(Enum(OrderType), default=OrderType.DELIVERY, nullable=False)
    delivery_address = Column(Text, nullable=True)
    order_status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    payment_method = Column(String(50), default="card", nullable=False)
    payment_reference = Column(String(150), index=True, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    promo_code = Column(String(50), nullable=True)
    tax = Column(Numeric(10, 2), default=0.00, nullable=False)
    delivery_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="orders")
    served_by_admin = relationship("Admin", back_populates="processed_orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="order", uselist=False)


class OrderItem(Base):
    """
    Individual line items within an order.
    """
    __tablename__ = "order_items"

    order_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id", ondelete="CASCADE"), index=True, nullable=False)
    dish_id = Column(UUID(as_uuid=True), ForeignKey("dishes.dish_id", ondelete="RESTRICT"), index=True, nullable=False)
    dish_name = Column(String(150), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    special_requests = Column(Text, nullable=True)

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")


class Reservation(Base):
    """
    Table dining reservation linking to configured seating areas.
    """
    __tablename__ = "reservations"

    reservation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_code = Column(String(20), unique=True, index=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    assigned_admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id", ondelete="SET NULL"), nullable=True)
    seating_area_id = Column(UUID(as_uuid=True), ForeignKey("seating_areas.seating_area_id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), nullable=False)
    reservation_date = Column(Date, index=True, nullable=False)
    reservation_time = Column(Time, nullable=False)
    guests_count = Column(Integer, default=2, nullable=False)
    special_requests = Column(Text, nullable=True)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED, nullable=False)
    table_number = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="reservations")
    assigned_admin = relationship("Admin", back_populates="assigned_reservations")
    seating_area = relationship("SeatingArea", back_populates="reservations")


class Review(Base):
    """
    Customer dining testimonials and ratings.
    """
    __tablename__ = "reviews"

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True)
    dish_id = Column(UUID(as_uuid=True), ForeignKey("dishes.dish_id", ondelete="SET NULL"), nullable=True)
    author_name = Column(String(100), nullable=False)
    author_location = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    rating = Column(Integer, default=5, nullable=False)
    quote = Column(Text, nullable=False)
    is_featured = Column(Boolean, default=False, index=True)
    is_approved = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="reviews")
    dish = relationship("Dish", back_populates="reviews")


class Promotion(Base):
    """
    Discount codes and promotional offers (e.g. OASIS5).
    """
    __tablename__ = "promotions"

    promo_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_type = Column(String(20), default="percentage", nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_order_amount = Column(Numeric(10, 2), default=0.00)
    max_uses = Column(Integer, nullable=True)
    times_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContactInquiry(Base):
    """
    Public contact form inquiries.
    """
    __tablename__ = "contact_inquiries"

    inquiry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(Enum(InquiryStatus), default=InquiryStatus.UNREAD, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Expense(Base):
    """
    Operating restaurant expenditures (raw ingredients, utilities, wages, maintenance).
    """
    __tablename__ = "expenses"

    expense_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_number = Column(String(30), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(Enum(ExpenseCategory), default=ExpenseCategory.KITCHEN_INGREDIENTS, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), default="cash", nullable=False)
    payment_reference = Column(String(150), nullable=True)
    vendor_name = Column(String(150), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    recorded_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id", ondelete="SET NULL"), nullable=True, index=True)
    expense_date = Column(Date, index=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    recorded_by = relationship("Admin", back_populates="recorded_expenses")
    transaction = relationship("Transaction", back_populates="expense", uselist=False)


class Transaction(Base):
    """
    Central financial transaction ledger recording all money entering and leaving Oasis Restaurant.
    """
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_number = Column(String(30), unique=True, index=True, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    category = Column(Enum(TransactionCategory), default=TransactionCategory.FOOD_SALES, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="GHS", nullable=False)
    payment_method = Column(String(50), default="cash", nullable=False)
    payment_reference = Column(String(150), index=True, nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, index=True)
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.expense_id", ondelete="SET NULL"), nullable=True, index=True)
    recorded_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.admin_id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    order = relationship("Order", back_populates="transaction")
    expense = relationship("Expense", back_populates="transaction")
    recorded_by = relationship("Admin", back_populates="recorded_transactions")


class AdminNotification(Base):
    """
    Central persistent notification log for admin & operational staff alerts (orders, reservations, system).
    """
    __tablename__ = "admin_notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type = Column(Enum(NotificationType), default=NotificationType.ORDER, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    reference_id = Column(String(100), nullable=True, index=True)
    data = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
