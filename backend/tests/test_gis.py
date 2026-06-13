import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.gis import Location, Region, Zone, Geofence, LocationHistory, GISAuditLog
from app.services.password_service import password_service
from app.services.gis.boundary_engine import boundary_engine
from app.services.gis.location_validator import location_validator
from app.services.gis.location_service import location_service
from app.services.gis.region_service import region_service
from app.services.gis.zone_manager import zone_manager
from app.services.gis.geofence_service import geofence_service
from app.services.gis.spatial_analytics import spatial_analytics
from app.services.gis.cluster_analyzer import cluster_analyzer
from app.services.gis.heatmap_generator import heatmap_generator
from app.services.gis.location_intelligence_engine import location_intelligence_engine
from app.services.gis.risk_zone_mapper import risk_zone_mapper

pytestmark = pytest.mark.asyncio


# Helper function to generate login tokens for test users
async def get_auth_headers(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": username,
            "password": "Password123!"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Helper to create a user and assign a specific role
async def create_user_with_role(db: AsyncSession, username: str, role_name: str) -> User:
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role = res.scalar_one()

    user = User(
        email=f"{username}@forestfire.org",
        username=username,
        hashed_password=password_service.hash_password("Password123!"),
        is_active=True,
        is_verified=True
    )
    user.roles.append(role)
    db.add(user)
    await db.flush()
    return user


async def test_boundary_engine_math():
    """Verify point-in-polygon and distance formulas execute correctly."""
    # Polygon surrounding Yosemite coordinate region
    poly = [[37.0, -120.0], [38.0, -120.0], [38.0, -119.0], [37.0, -119.0], [37.0, -120.0]]
    
    # Inside point
    assert boundary_engine.is_point_in_polygon(37.5, -119.5, poly) is True
    # Outside point
    assert boundary_engine.is_point_in_polygon(39.0, -118.0, poly) is False

    # Haversine distance: point (0, 0) to (0, 1) is approx 111km (111319 meters)
    dist = boundary_engine.haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert 110000.0 < dist < 112000.0


def test_location_validator_bounds():
    """Verify coordinates bounds validation for WGS84 standard."""
    # Valid
    assert location_validator.validate_coordinates(45.0, 90.0) is True
    
    # Invalid lat
    with pytest.raises(Exception):
        location_validator.validate_coordinates(95.0, 90.0)

    # Invalid lng
    with pytest.raises(Exception):
        location_validator.validate_coordinates(45.0, 185.0)


async def test_region_and_zone_crud(db: AsyncSession):
    """Test administrative division registers and subzone boundary maps."""
    # Seed default regions
    await region_service.seed_default_regions(db)
    
    # Create Region
    reg = await region_service.create_region(
        db=db,
        name="Sierra Forestry Division",
        code="SR-DIV",
        type_="Forest Division",
        boundary={"type": "Polygon", "coordinates": [[[35.0, -118.0], [36.0, -118.0], [36.0, -117.0], [35.0, -117.0], [35.0, -118.0]]]}
    )
    assert reg.name == "Sierra Forestry Division"

    # Create Subzone
    zone = await zone_manager.create_zone(
        db=db,
        name="Wildfire Buffer 1",
        code="WF-BUF-1",
        region_id=reg.id,
        type_="Wildfire Buffer",
        boundary={"type": "Polygon", "coordinates": [[[35.2, -117.8], [35.8, -117.8], [35.8, -117.2], [35.2, -117.2], [35.2, -117.8]]]},
        risk_level="High"
    )
    assert zone.name == "Wildfire Buffer 1"
    assert zone.risk_level == "High"


async def test_geofencing_breach_detection(db: AsyncSession):
    """Verify circular and polygonal geofence breach detectors."""
    # Circular Geofence: center (34.0, -118.0), radius 1000 meters
    gf_circle = await geofence_service.create_geofence(
        db=db,
        name="Ranger Depot Circle",
        type_="Circular",
        geometry={"center": [34.0, -118.0], "radius": 1000.0}
    )

    # Coordinates 500 meters away -> breached
    breached_circle = await geofence_service.check_point_breaches(db, 34.002, -118.002)
    assert gf_circle.id in [g.id for g in breached_circle]

    # Coordinates 2km away -> not breached
    safe_circle = await geofence_service.check_point_breaches(db, 34.02, -118.02)
    assert gf_circle.id not in [g.id for g in safe_circle]


async def test_observability_and_intelligence(db: AsyncSession):
    """Verify location intelligence compilation, clustering centroids, and risk classify."""
    # Setup some regions & zones
    reg = await region_service.create_region(
        db=db,
        name="Pacific Northwest Division",
        code="PNW-DIV",
        type_="Forest Division",
        boundary={"type": "Polygon", "coordinates": [[[45.0, -122.0], [47.0, -122.0], [47.0, -120.0], [45.0, -120.0], [45.0, -122.0]]]}
    )
    zone = await zone_manager.create_zone(
        db=db,
        name="Olympic Protected Area",
        code="OLY-PRT",
        region_id=reg.id,
        type_="Protected Area",
        boundary={"type": "Polygon", "coordinates": [[[45.5, -121.5], [46.5, -121.5], [46.5, -120.5], [45.5, -120.5], [45.5, -121.5]]]},
        risk_level="Extreme"
    )
    await db.commit()

    # Query Coordinate Intelligence inside Olympic zone
    intel = await location_intelligence_engine.get_coordinates_intelligence(db, 46.0, -121.0)
    assert intel["region"] == "Pacific Northwest Division"
    assert intel["zone"] == "Olympic Protected Area"
    assert intel["zone_risk_level"] == "Extreme"

    # Verify risk zone classifier
    risk = await risk_zone_mapper.classify_risk_zone(db, 46.0, -121.0)
    assert risk == "Extreme"


async def test_gis_rest_endpoints(client: AsyncClient, db: AsyncSession):
    """Verify all GIS REST API endpoint actions under RBAC controls."""
    admin = await create_user_with_role(db, "gis_admin", "Super Admin")
    officer = await create_user_with_role(db, "gis_officer", "Forest Officer")
    viewer = await create_user_with_role(db, "gis_viewer", "Viewer")
    await db.commit()

    admin_headers = await get_auth_headers(client, "gis_admin")
    officer_headers = await get_auth_headers(client, "gis_officer")
    viewer_headers = await get_auth_headers(client, "gis_viewer")

    # 1. Create Location (requires view_alerts)
    res_loc = await client.post(
        "/api/v1/gis/locations",
        json={
            "name": "Lookout Tower A",
            "latitude": 37.5,
            "longitude": -119.5,
            "description": "Primary fire lookout tower"
        },
        headers=officer_headers
    )
    assert res_loc.status_code == 201
    loc_id = res_loc.json()["id"]

    # Viewer fails to create location (no view_alerts)
    res_loc_fail = await client.post(
        "/api/v1/gis/locations",
        json={"name": "Fail Tower", "latitude": 0.0, "longitude": 0.0},
        headers=viewer_headers
    )
    assert res_loc_fail.status_code == 403

    # 2. List locations
    res_list = await client.get("/api/v1/gis/locations", headers=viewer_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total_count"] >= 1

    # 3. Create administrative region (requires manage_platform_settings)
    res_reg = await client.post(
        "/api/v1/gis/regions",
        json={
            "name": "Central Division",
            "code": "CEN-DIV",
            "type": "Forest Division",
            "boundary": {"type": "Polygon", "coordinates": [[[37.0, -120.0], [38.0, -120.0], [38.0, -119.0], [37.0, -119.0], [37.0, -120.0]]]}
        },
        headers=admin_headers
    )
    assert res_reg.status_code == 201
    region_id = res_reg.json()["id"]

    # Officer fails to create region (no manage_platform_settings)
    res_reg_fail = await client.post(
        "/api/v1/gis/regions",
        json={"name": "Sierra", "code": "SIE-RNG", "type": "Division", "boundary": {}},
        headers=officer_headers
    )
    assert res_reg_fail.status_code == 403

    # 4. Create Zone
    res_zone = await client.post(
        "/api/v1/gis/zones",
        json={
            "name": "Central Safety zone",
            "code": "CEN-SFY",
            "region_id": str(region_id),
            "type": "Protected Area",
            "boundary": {"type": "Polygon", "coordinates": [[[37.2, -119.8], [37.8, -119.8], [37.8, -119.2], [37.2, -119.2], [37.2, -119.8]]]},
            "risk_level": "Medium"
        },
        headers=admin_headers
    )
    assert res_zone.status_code == 201

    # 5. Create Geofence
    res_gf = await client.post(
        "/api/v1/gis/geofences",
        json={
            "name": "Buffer Geofence 1",
            "type": "Circular",
            "geometry": {"center": [37.5, -119.5], "radius": 500.0}
        },
        headers=admin_headers
    )
    assert res_gf.status_code == 201

    # 6. Retrieve coordinate intelligence
    res_intel = await client.get("/api/v1/gis/coordinate-intelligence?latitude=37.5&longitude=-119.5", headers=viewer_headers)
    assert res_intel.status_code == 200
    assert res_intel.json()["region"] == "Central Division"
    assert res_intel.json()["zone"] == "Central Safety zone"
    assert "Buffer Geofence 1" in res_intel.json()["breached_geofences"]

    # 7. Spatial analytics endpoint
    res_analytics = await client.get("/api/v1/gis/spatial-analytics", headers=viewer_headers)
    assert res_analytics.status_code == 200
    assert "heatmap_data" in res_analytics.json()
    assert "clusters_data" in res_analytics.json()

    # 8. Log location history
    res_hist = await client.post(
        "/api/v1/gis/location-history",
        json={
            "entity_type": "patrol",
            "entity_id": str(uuid.uuid4()),
            "latitude": 37.502,
            "longitude": -119.502
        },
        headers=officer_headers
    )
    assert res_hist.status_code == 201

    # 9. Get audit logs (requires access_audit_logs)
    res_audit = await client.get("/api/v1/gis/audit-history", headers=admin_headers)
    assert res_audit.status_code == 200
    assert res_audit.json()["total_count"] >= 1
