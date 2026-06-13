from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard_controller import router as dashboard_router
from app.api.v1.dataset_controller import router as dataset_router
from app.api.v1.image_controller import router as image_router
from app.api.v1.training_controller import router as training_router
from app.api.v1.prediction_controller import router as prediction_router
from app.api.v1.alert_controller import router as alert_router

v1_router = APIRouter()
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
v1_router.include_router(dataset_router, prefix="/datasets", tags=["Dataset Management"])
v1_router.include_router(image_router, prefix="/images", tags=["Image Upload & Storage"])
v1_router.include_router(training_router, prefix="/training", tags=["CNN Training Pipeline"])
v1_router.include_router(prediction_router, prefix="/predictions", tags=["CNN Inference & Prediction Engine"])
v1_router.include_router(alert_router, prefix="/alerts", tags=["Fire Detection Alert Management System"])
