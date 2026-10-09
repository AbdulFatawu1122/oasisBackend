import os
from typing import Annotated
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from fastapi import Depends

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "oasis_super_secure_secret_jwt_key_tamale_2026_oasis")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))

# PostgreSQL Database Connection
# Prioritizes APP_POSTGRES_DB_URL, then DATABASE_URL
DATABASE_URL = (
    os.getenv("APP_POSTGRES_DB_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycopg://oasis_app:0827@localhost:5432/oasis_db"
)

# Normalize PostgreSQL driver prefix to psycopg (SQLAlchemy 2.0 recommended)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


def get_db():
    """
    Standard PostgreSQL database session generator dependency.
    Yields a Session instance and guarantees session closure after request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
