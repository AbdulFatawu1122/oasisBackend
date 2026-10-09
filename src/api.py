from fastapi import FastAPI

from src.admin_auth.controller import router as admin_auth_router
from src.auth.controller import router as auth_router
from src.menu.controller import router as menu_router
from src.seating.controller import router as seating_router
from src.reservations.controller import router as reservations_router
from src.orders.controller import router as orders_router
from src.reviews.controller import router as reviews_router
from src.contact.controller import router as contact_router
from src.finance.controller import router as finance_router
from src.notifications.controller import router as notifications_router
from src.websocket.controller import router as ws_router


def register_routes(app: FastAPI):
    """
    Registers all domain controllers directly with the FastAPI application under /api/v1.
    Strictly follows the register_routes pattern from uniqkid_backend.
    """
    prefix = "/api/v1"
    app.include_router(admin_auth_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(menu_router, prefix=prefix)
    app.include_router(seating_router, prefix=prefix)
    app.include_router(reservations_router, prefix=prefix)
    app.include_router(orders_router, prefix=prefix)
    app.include_router(reviews_router, prefix=prefix)
    app.include_router(contact_router, prefix=prefix)
    app.include_router(finance_router, prefix=prefix)
    app.include_router(notifications_router, prefix=prefix)

    # WebSocket router available under both /api/v1/ws/admin and /ws/admin
    app.include_router(ws_router, prefix=prefix)
    app.include_router(ws_router)
