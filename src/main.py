import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

from .database.core import Base, engine
from .api import register_routes

load_dotenv()

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("oasis_backend")

is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schemas (including admin_notifications) exist
    try:
        from .entities import entities
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas verified and initialized.")
    except Exception as e:
        logger.warning(f"Could not auto-create database tables on startup: {e}")
    yield


app = FastAPI(
    title="Oasis Restaurant API",
    description="Backend API for Oasis Restaurant - Menu, Orders, Table Reservations & RBAC Staff Operations",
    version="1.0.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware for Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

# Automatic response compression for payloads >= 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Register all modular domain routers
register_routes(app=app)


@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Oasis Restaurant API"
    }
