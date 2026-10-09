from datetime import date
from typing import List, Optional
from fastapi import APIRouter, status, Depends, Query

from src.database.core import DbSession
from src.entities.entities import Admin, ExpenseCategory, TransactionType
from src.admin_auth.service import RequireAdmin
from . import models, service

router = APIRouter(
    prefix="/finance",
    tags=["Financials & Cash Ledger"]
)


@router.post("/expenses", response_model=models.ExpenseResponse, status_code=status.HTTP_201_CREATED)
def record_expense(
    payload: models.ExpenseCreate,
    db: DbSession,
    staff: Admin = RequireAdmin,
):
    """
    Log an operating expense (raw materials, utilities, wages).
    Automatically records debit in central transaction ledger.
    """
    return service.create_expense(payload=payload, admin_id=staff.admin_id, db=db)


@router.get("/expenses", response_model=List[models.ExpenseResponse])
def get_expenses(
    db: DbSession,
    category: Optional[ExpenseCategory] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: Admin = RequireAdmin,
):
    """List operational restaurant expenses with optional date/category filters."""
    return service.list_expenses(
        db=db,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/transactions", response_model=List[models.TransactionResponse])
def get_transactions(
    db: DbSession,
    type: Optional[TransactionType] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: Admin = RequireAdmin,
):
    """View central ledger entries (all incoming and outgoing cash flow)."""
    return service.list_transactions(db=db, trx_type=type, limit=limit)


@router.get("/analytics", response_model=models.DashboardAnalyticsResponse)
def get_dashboard_analytics(
    db: DbSession,
    timeframe: str = Query("monthly", description="monthly, weekly, or today for revenue curve"),
    orders_timeframe: Optional[str] = Query(None, description="monthly, weekly, or today for orders summary"),
    _: Admin = RequireAdmin,
):
    """
    Executive financial and operational metrics for the Odama Studio Dashboard.
    Returns real revenue curves, orders summaries, and KPI cards.
    """
    return service.get_dashboard_analytics(
        timeframe=timeframe,
        orders_timeframe=orders_timeframe,
        db=db,
    )
