from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from src.entities.entities import TransactionType, TransactionCategory, ExpenseCategory


class ExpenseCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    category: ExpenseCategory = ExpenseCategory.KITCHEN_INGREDIENTS
    amount: float = Field(..., gt=0)
    payment_method: str = "cash"
    payment_reference: Optional[str] = None
    vendor_name: Optional[str] = None
    receipt_url: Optional[str] = None
    expense_date: Optional[date] = None
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    expense_id: UUID
    expense_number: str
    title: str
    category: ExpenseCategory
    amount: float
    payment_method: str
    payment_reference: Optional[str] = None
    vendor_name: Optional[str] = None
    receipt_url: Optional[str] = None
    expense_date: date
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    transaction_id: UUID
    reference_number: str
    transaction_type: TransactionType
    category: TransactionCategory
    amount: float
    currency: str
    payment_method: str
    payment_reference: Optional[str] = None
    order_id: Optional[UUID] = None
    expense_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FinanceSummaryResponse(BaseModel):
    total_income: float
    total_expenses: float
    net_profit: float
    today_income: float
    today_expenses: float
    today_orders_count: int
    total_menus_count: int
    in_stock_ratio: int
    total_clients_today: int
    revenue_day_ratio: float
    currency: str = "GHS"


class RevenueCurvePoint(BaseModel):
    label: str
    income: float
    expenses: float


class OrdersSummaryPoint(BaseModel):
    label: str
    dine_in_count: int
    delivery_pickup_count: int


class DashboardAnalyticsResponse(BaseModel):
    summary: FinanceSummaryResponse
    revenue_curve: List[RevenueCurvePoint]
    orders_summary: List[OrdersSummaryPoint]
