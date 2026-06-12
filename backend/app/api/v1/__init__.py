from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard_controller import router as dashboard_router

v1_router = APIRouter()
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
