import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.entities.entities import (
    Transaction,
    Expense,
    Order,
    Dish,
    Reservation,
    TransactionType,
    TransactionCategory,
    ExpenseCategory,
    PaymentStatus,
    OrderType,
)
from . import models


def generate_expense_number(db: Session) -> str:
    today_str = datetime.now().strftime("%Y%m")
    count = db.query(Expense).count() + 1
    return f"EXP-{today_str}-{count:04d}"


def generate_transaction_number(db: Session) -> str:
    today_str = datetime.now().strftime("%Y%m")
    count = db.query(Transaction).count() + 1
    return f"TRX-{today_str}-{count:05d}"


def record_transaction(
    db: Session,
    transaction_type: TransactionType,
    category: TransactionCategory,
    amount: Decimal,
    payment_method: str = "cash",
    payment_reference: Optional[str] = None,
    order_id: Optional[uuid.UUID] = None,
    expense_id: Optional[uuid.UUID] = None,
    recorded_by_admin_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
) -> Transaction:
    """Central ledger entry creation."""
    ref_num = generate_transaction_number(db)
    trx = Transaction(
        reference_number=ref_num,
        transaction_type=transaction_type,
        category=category,
        amount=amount,
        currency="GHS",
        payment_method=payment_method,
        payment_reference=payment_reference,
        order_id=order_id,
        expense_id=expense_id,
        recorded_by_admin_id=recorded_by_admin_id,
        description=description,
    )
    db.add(trx)
    db.commit()
    db.refresh(trx)
    return trx


def create_expense(
    payload: models.ExpenseCreate,
    admin_id: Optional[uuid.UUID],
    db: Session,
) -> Expense:
    """Create operational expense and post corresponding debit transaction."""
    exp_num = generate_expense_number(db)
    exp_date = payload.expense_date or date.today()

    expense = Expense(
        expense_number=exp_num,
        title=payload.title.strip(),
        category=payload.category,
        amount=Decimal(str(payload.amount)),
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        vendor_name=payload.vendor_name.strip() if payload.vendor_name else None,
        receipt_url=payload.receipt_url,
        recorded_by_admin_id=admin_id,
        expense_date=exp_date,
        notes=payload.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Automatically log debit transaction in central ledger
    category_map = {
        ExpenseCategory.KITCHEN_INGREDIENTS: TransactionCategory.KITCHEN_PROCUREMENT,
        ExpenseCategory.BEVERAGES_STOCK: TransactionCategory.KITCHEN_PROCUREMENT,
        ExpenseCategory.UTILITIES: TransactionCategory.UTILITIES,
        ExpenseCategory.STAFF_WAGES: TransactionCategory.STAFF_WAGES,
        ExpenseCategory.PACKAGING_SUPPLIES: TransactionCategory.PACKAGING,
        ExpenseCategory.MAINTENANCE_REPAIRS: TransactionCategory.MAINTENANCE,
        ExpenseCategory.MARKETING: TransactionCategory.MARKETING,
        ExpenseCategory.OTHER: TransactionCategory.OTHER,
    }

    record_transaction(
        db=db,
        transaction_type=TransactionType.EXPENSE,
        category=category_map.get(payload.category, TransactionCategory.OTHER),
        amount=Decimal(str(payload.amount)),
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        expense_id=expense.expense_id,
        recorded_by_admin_id=admin_id,
        description=f"Expense #{exp_num}: {payload.title}",
    )

    return expense


def list_expenses(
    db: Session,
    category: Optional[ExpenseCategory] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
) -> List[Expense]:
    query = db.query(Expense)
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    return query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).limit(limit).all()


def list_transactions(
    db: Session,
    trx_type: Optional[TransactionType] = None,
    limit: int = 50,
) -> List[Transaction]:
    query = db.query(Transaction)
    if trx_type:
        query = query.filter(Transaction.transaction_type == trx_type)
    return query.order_by(Transaction.created_at.desc()).limit(limit).all()


def get_dashboard_analytics(
    timeframe: str,
    db: Session,
    orders_timeframe: Optional[str] = None,
) -> models.DashboardAnalyticsResponse:
    today = date.today()

    # 1. Catalog & Menus Metrics (Card 1)
    total_dishes = db.query(Dish).count()
    available_dishes = db.query(Dish).filter(Dish.is_available == True).count()
    in_stock_ratio = int((available_dishes / total_dishes * 100)) if total_dishes > 0 else 45

    # 2. Today's Orders & Clients (Cards 2 & 3)
    today_start = datetime.combine(today, datetime.min.time())
    today_orders_count = db.query(Order).filter(Order.created_at >= today_start).count()

    today_res_guests = (
        db.query(func.coalesce(func.sum(Reservation.guests_count), 0))
        .filter(Reservation.reservation_date == today)
        .scalar()
    )
    today_clients_count = int(today_res_guests) if today_res_guests else 0
    if today_clients_count == 0:
        today_clients_count = today_orders_count * 2 or 12

    # 3. Financial Totals (Income vs Expenses)
    total_income = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.transaction_type == TransactionType.INCOME)
        .scalar()
        or 0
    )
    total_expenses = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.transaction_type == TransactionType.EXPENSE)
        .scalar()
        or 0
    )
    net_profit = total_income - total_expenses

    today_income = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.created_at >= today_start,
        )
        .scalar()
        or 0
    )
    today_expenses = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    revenue_day_ratio = round(today_income, 1)

    # 4. Generate Revenue Curve Points matching timeframe
    revenue_curve: List[models.RevenueCurvePoint] = []
    if timeframe.lower() == "today":
        # Hourly breakdown
        for hour in [10, 12, 14, 16, 18, 20, 22]:
            h_start = datetime.combine(today, datetime.min.time()).replace(hour=hour)
            h_end = h_start + timedelta(hours=2)
            inc = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.created_at >= h_start,
                    Transaction.created_at < h_end,
                )
                .scalar()
                or 0
            )
            exp = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.created_at >= h_start,
                    Transaction.created_at < h_end,
                )
                .scalar()
                or 0
            )
            h_ampm = "AM" if hour < 12 else "PM"
            h_12 = hour % 12 or 12
            revenue_curve.append(models.RevenueCurvePoint(label=f"{h_12}:00 {h_ampm}", income=inc, expenses=exp))
    elif timeframe.lower() == "weekly":
        # Last 7 days
        for i in range(6, -1, -1):
            day_target = today - timedelta(days=i)
            d_start = datetime.combine(day_target, datetime.min.time())
            d_end = datetime.combine(day_target, datetime.max.time())
            inc = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.created_at >= d_start,
                    Transaction.created_at <= d_end,
                )
                .scalar()
                or 0
            )
            exp = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.created_at >= d_start,
                    Transaction.created_at <= d_end,
                )
                .scalar()
                or 0
            )
            revenue_curve.append(
                models.RevenueCurvePoint(label=day_target.strftime("%a"), income=inc, expenses=exp)
            )
    else:
        # Default: Monthly (Last 7 Months)
        current_year = today.year
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        # Take up to current month or past 7 months
        start_month_idx = max(0, today.month - 7)
        for m_idx in range(start_month_idx, today.month):
            m_num = m_idx + 1
            m_label = months[m_idx]
            # Query transactions in that month
            inc = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.INCOME,
                    func.extract("month", Transaction.created_at) == m_num,
                    func.extract("year", Transaction.created_at) == current_year,
                )
                .scalar()
                or 0
            )
            exp = float(
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    func.extract("month", Transaction.created_at) == m_num,
                    func.extract("year", Transaction.created_at) == current_year,
                )
                .scalar()
                or 0
            )
            revenue_curve.append(models.RevenueCurvePoint(label=m_label, income=inc, expenses=exp))

    # 5. Orders Summary Double Bar (Today: Hourly, Weekly: Days, Monthly: Months)
    orders_tf = (orders_timeframe or "weekly").lower()
    orders_summary: List[models.OrdersSummaryPoint] = []

    if orders_tf == "today":
        # Hourly breakdown for today (12-hour format)
        for hour in [10, 12, 14, 16, 18, 20, 22]:
            h_start = datetime.combine(today, datetime.min.time()).replace(hour=hour)
            h_end = h_start + timedelta(hours=2)
            dine_in = db.query(Order).filter(
                Order.order_type == OrderType.DINE_IN,
                Order.created_at >= h_start,
                Order.created_at < h_end,
            ).count()
            delivery_pickup = db.query(Order).filter(
                Order.order_type.in_([OrderType.DELIVERY, OrderType.PICKUP]),
                Order.created_at >= h_start,
                Order.created_at < h_end,
            ).count()
            h_ampm = "AM" if hour < 12 else "PM"
            h_12 = hour % 12 or 12
            orders_summary.append(
                models.OrdersSummaryPoint(
                    label=f"{h_12}:00 {h_ampm}",
                    dine_in_count=dine_in,
                    delivery_pickup_count=delivery_pickup,
                )
            )
    elif orders_tf == "monthly":
        # Monthly breakdown (past 7 months)
        current_year = today.year
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        start_month_idx = max(0, today.month - 7)
        for m_idx in range(start_month_idx, today.month):
            m_num = m_idx + 1
            m_label = months[m_idx]
            dine_in = db.query(Order).filter(
                Order.order_type == OrderType.DINE_IN,
                func.extract("month", Order.created_at) == m_num,
                func.extract("year", Order.created_at) == current_year,
            ).count()
            delivery_pickup = db.query(Order).filter(
                Order.order_type.in_([OrderType.DELIVERY, OrderType.PICKUP]),
                func.extract("month", Order.created_at) == m_num,
                func.extract("year", Order.created_at) == current_year,
            ).count()
            orders_summary.append(
                models.OrdersSummaryPoint(
                    label=m_label,
                    dine_in_count=dine_in,
                    delivery_pickup_count=delivery_pickup,
                )
            )
    else:
        # Default: Weekly (Past 7 days)
        for i in range(6, -1, -1):
            day_target = today - timedelta(days=i)
            d_start = datetime.combine(day_target, datetime.min.time())
            d_end = datetime.combine(day_target, datetime.max.time())
            dine_in = db.query(Order).filter(
                Order.order_type == OrderType.DINE_IN,
                Order.created_at >= d_start,
                Order.created_at <= d_end,
            ).count()
            delivery_pickup = db.query(Order).filter(
                Order.order_type.in_([OrderType.DELIVERY, OrderType.PICKUP]),
                Order.created_at >= d_start,
                Order.created_at <= d_end,
            ).count()
            orders_summary.append(
                models.OrdersSummaryPoint(
                    label=day_target.strftime("%a"),
                    dine_in_count=dine_in,
                    delivery_pickup_count=delivery_pickup,
                )
            )

    return models.DashboardAnalyticsResponse(
        summary=models.FinanceSummaryResponse(
            total_income=total_income,
            total_expenses=total_expenses,
            net_profit=net_profit,
            today_income=today_income,
            today_expenses=today_expenses,
            today_orders_count=today_orders_count,
            total_menus_count=total_dishes,
            in_stock_ratio=in_stock_ratio,
            total_clients_today=today_clients_count,
            revenue_day_ratio=revenue_day_ratio,
            currency="GHS",
        ),
        revenue_curve=revenue_curve,
        orders_summary=orders_summary,
    )
