import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.database import Base, get_db

# Test Database URI (uses in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocalTest = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False
)

# Track whether the DB has been initialised for this process
_db_initialised = False


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialise tables and seed roles once per process, then yield per-test."""
    global _db_initialised
    if not _db_initialised:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with SessionLocalTest() as db:
            from app.services.permission_service import permission_service
            await permission_service.seed_roles_and_permissions(db)
            await db.commit()

        _db_initialised = True
    yield


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session per test, rolling back after."""
    async with SessionLocalTest() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture with overridden database dependency."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
