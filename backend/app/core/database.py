from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Determine if the database is SQLite to enable SQLite-specific options
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Configure async engine
# For SQLite, we avoid pool size configurations that are unsupported
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args, future=True)

# Enable foreign keys for SQLite sessions
if is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create async sessionmaker
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False)


# Base class for SQLAlchemy 2.x models
class Base(DeclarativeBase):
    pass


# DB session dependency injection helper
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db_session:
        try:
            yield db_session
        finally:
            await db_session.close()
