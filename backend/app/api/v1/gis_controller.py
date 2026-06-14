import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.user import User
from app.models.detection import Detection
from app.models.gis import Location, Region, Zone, Geofence, LocationHistory, AlertLocation
from app.schemas.gis_schema import (
    LocationResponse,
    LocationCreateRequest,
    RegionResponse,
    RegionCreateRequest,
    ZoneResponse,
    ZoneCreateRequest,
    GeofenceResponse,
    GeofenceCreateRequest,
    LocationHistoryResponse,
    LocationHistoryCreateRequest,
    GISHistoryListResponse,
    GISRegionListResponse,
    GISZoneListResponse,
    GISGeofenceListResponse,
    GISAuditHistoryResponse,
    AlertLocationResponse,
)
from app.repositories.location_repository import location_repository
from app.services.gis.location_service import location_service
from app.services.gis.region_service import region_service
from app.services.gis.zone_manager import zone_manager
from app.services.gis.geofence_service import geofence_service
from app.services.gis.spatial_analytics import spatial_analytics
from app.services.gis.location_intelligence_engine import location_intelligence_engine
from app.services.gis.gis_monitor import gis_monitor

router = APIRouter()


@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """Register a new location coordinate reference point."""
    loc = await location_service.create_location(
        db=db,
        name=body.name,
        latitude=body.latitude,
        longitude=body.longitude,
        address=body.address,
        elevation=body.elevation,
        description=body.description,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(loc)
    return loc


@router.get("/locations", response_model=GISHistoryListResponse)
async def list_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve all locations with optional filtering."""
    items, total = await location_repository.get_locations_filtered(db, skip, limit, name)
    return {"items": items, "total_count": total}


@router.get("/locations/{id}", response_model=LocationResponse)
async def get_location(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """View details of a single geocoded reference location."""
    return await location_service.get_location_by_id(db, id)


@router.post("/regions", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
async def create_region(
    body: RegionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Register a new administrative division or forest range polygon boundary."""
    region = await region_service.create_region(
        db=db,
        name=body.name,
        code=body.code,
        type_=body.type,
        boundary=body.boundary,
        parent_id=body.parent_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(region)
    return region


@router.get("/regions", response_model=GISRegionListResponse)
async def list_regions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type_: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve administrative division regions."""
    items, total = await location_repository.get_regions_filtered(db, skip, limit, type_)
    return {"items": items, "total_count": total}


@router.get("/regions/{id}", response_model=RegionResponse)
async def get_region(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """View polygon boundary details for a single region division."""
    return await region_service.get_region_by_id(db, id)


@router.post("/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    body: ZoneCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Register a new monitoring division or buffer zone polygon boundary."""
    zone = await zone_manager.create_zone(
        db=db,
        name=body.name,
        code=body.code,
        region_id=body.region_id,
        type_=body.type,
        boundary=body.boundary,
        risk_level=body.risk_level,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(zone)
    return zone


@router.get("/zones", response_model=GISZoneListResponse)
async def list_zones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    region_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve monitoring buffer zones."""
    items, total = await location_repository.get_zones_filtered(db, skip, limit, region_id)
    return {"items": items, "total_count": total}


@router.post("/geofences", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
async def create_geofence(
    body: GeofenceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Register a new circular/polygonal geofence boundary."""
    geofence = await geofence_service.create_geofence(
        db=db,
        name=body.name,
        description=body.description,
        type_=body.type,
        geometry=body.geometry,
        is_active=body.is_active,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(geofence)
    return geofence


@router.get("/geofences", response_model=GISGeofenceListResponse)
async def list_geofences(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve geofencing entries."""
    items, total = await location_repository.get_geofences_filtered(db, skip, limit, is_active)
    return {"items": items, "total_count": total}


@router.get("/fire-locations", response_model=List[AlertLocationResponse])
async def list_fire_locations(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """Retrieve coordinates reference mappings for active fire alerts."""
    query = select(AlertLocation).options(selectinload(AlertLocation.location)).order_by(desc(AlertLocation.created_at))
    res = await db.execute(query)
    return list(res.scalars().all())


@router.get("/spatial-analytics")
async def get_spatial_analytics_report(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """Retrieve spatial clustering, hot wildfire spots, and heatmaps compilation."""
    gis_monitor.increment("spatial_queries")
    return await spatial_analytics.get_spatial_analytics_report(db)


@router.get("/coordinate-intelligence")
async def get_coordinate_intelligence(
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Compiles containment and geofencing context for point coordinates."""
    gis_monitor.increment("spatial_queries")
    return await location_intelligence_engine.get_coordinates_intelligence(db, latitude, longitude)


@router.post("/location-history", response_model=LocationHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_location_history(
    body: LocationHistoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """Log tracking history coordinate for ranger patrols or drone flights."""
    history = LocationHistory(
        entity_type=body.entity_type, entity_id=body.entity_id, latitude=body.latitude, longitude=body.longitude
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


@router.get("/audit-history", response_model=GISAuditHistoryResponse)
async def list_gis_audit_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs")),
):
    """View paginated security audit history logs for geofence breaches and spatial transactions."""
    items, total = await location_repository.get_gis_audit_history(db, skip, limit)
    return {"logs": items, "total_count": total}
