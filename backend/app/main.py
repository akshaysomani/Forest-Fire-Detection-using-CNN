from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.exceptions import register_exception_handlers
from app.api.v1 import v1_router
from app.services.permission_service import permission_service
from app.models.user import User
from app.models.role import Role
from app.services.password_service import password_service
from app.middleware.rate_limit import RateLimitMiddleware
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (convenient for local run / testing)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial roles, permissions, and admin user
    async with SessionLocal() as db:
        try:
            await permission_service.seed_roles_and_permissions(db)
            
            # Seed default dataset categories and labels
            from app.services.dataset_service import dataset_service
            await dataset_service.seed_categories_and_labels(db)

            # Seed default regions
            from app.services.gis.region_service import region_service
            await region_service.seed_default_regions(db)

            # Check if default Super Admin already exists
            admin_query = select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
            res = await db.execute(admin_query)
            admin = res.scalar_one_or_none()

            if not admin:
                # Find Super Admin role
                role_query = select(Role).where(Role.name == "Super Admin")
                role_res = await db.execute(role_query)
                admin_role = role_res.scalar_one_or_none()

                hashed_pwd = password_service.hash_password(settings.DEFAULT_ADMIN_PASSWORD)
                new_admin = User(
                    email=settings.DEFAULT_ADMIN_EMAIL,
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    hashed_password=hashed_pwd,
                    is_active=True,
                    is_verified=True
                )
                if admin_role:
                    new_admin.roles.append(admin_role)
                db.add(new_admin)
                await db.commit()
            else:
                await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Startup seeding error: {e}")

    # Start Event Bus background workers
    from app.services.alert import queue_manager
    from app.services.incident.incident_scheduler import incident_scheduler
    from app.services.analytics.aggregation_scheduler import aggregation_scheduler
    from app.services.analytics.report_scheduler import report_scheduler
    from app.services.analytics.analytics_processor import analytics_processor
    from app.services.alert.event_bus import event_bus

    queue_manager.start_alert_queue()
    incident_scheduler.start()
    aggregation_scheduler.start()
    report_scheduler.start()

    # Register analytics event bus subscribers
    event_bus.subscribe("alert_generated", analytics_processor.handle_alert_generated)
    event_bus.subscribe("alert_escalated", analytics_processor.handle_alert_escalated)
    event_bus.subscribe("geofence_breached", analytics_processor.handle_geofence_breached)

    yield
    # Shutdown actions
    await report_scheduler.stop()
    await aggregation_scheduler.stop()
    await incident_scheduler.stop()
    await queue_manager.stop_alert_queue()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware config
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register Rate Limiting Middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    auth_requests_per_minute=5
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    return response


# Register custom global exception handlers
register_exception_handlers(app)

# Include main router
app.include_router(v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    """Simple status check for container/orchestrator monitoring."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}
