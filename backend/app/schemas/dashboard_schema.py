import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class DashboardOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_users: int
    active_users: int
    total_uploaded_images: int
    images_processed: int
    fire_detections: int
    non_fire_detections: int
    detection_accuracy: float


class ModelUsageStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_name: str
    model_version: str
    count: int
    average_confidence: float


class DashboardStatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_users: int
    active_users: int
    total_uploaded_images: int
    images_processed: int
    fire_detections: int
    non_fire_detections: int
    detection_accuracy: float
    model_usage_statistics: List[ModelUsageStat]
    average_confidence: float


class ActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class RecentActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activities: List[ActivityItem]
    total_count: int


class StorageUsageInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_bytes: int
    used_bytes: int
    free_bytes: int
    percentage_used: float


class MemoryUsageInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_bytes: int
    used_bytes: int
    free_bytes: int
    percentage_used: float


class SystemSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    api_status: str
    database_status: str
    storage_usage: StorageUsageInfo
    cpu_usage_percent: float
    memory_usage: MemoryUsageInfo
    active_sessions: int
    background_jobs_status: str
    queue_status: str


class RoleCount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_name: str
    count: int


class UserGrowthData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_bucket: str
    count: int


class UserSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_users: int
    active_users: int
    verified_users: int
    role_distribution: List[RoleCount]
    user_growth_trend: List[UserGrowthData]
