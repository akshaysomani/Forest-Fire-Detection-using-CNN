import io
import pytest
import uuid
import zipfile
from datetime import datetime, timedelta
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.image import Image as ImageModel, ImageMetadata, ImageVersion, ImageStorageLocation
from app.services.image_validator import image_validator
from app.services.integrity_checker import integrity_checker
from app.services.image_preprocessor import image_preprocessor
from app.services.image_transformer import image_transformer
from app.services.thumbnail_service import thumbnail_service
from app.services.image_optimizer import image_optimizer
from app.services.cache_manager import cache_manager
from app.services.storage_optimizer import storage_optimizer
from app.services.file_storage_manager import file_storage_manager
from app.services.storage_service import storage_service
from app.repositories.image_repository import image_storage_location_repository, image_repository

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def mock_session_local(monkeypatch):
    from tests.conftest import SessionLocalTest
    import app.services.upload_processor as up_proc
    monkeypatch.setattr(up_proc, "SessionLocal", SessionLocalTest)


def create_test_image(format="PNG", size=(200, 200), color="red") -> bytes:
    """Helper to generate valid image bytes with correct headers."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


async def get_auth_headers(client: AsyncClient, role_name: str, db: AsyncSession) -> dict:
    """Helper to register and login a user with a specific seeded role."""
    username = f"user_{role_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
    email = f"{username}@forest.org"
    password = "SuperPassword123!"

    # 1. Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "confirm_password": password
        }
    )
    assert reg_res.status_code == 201

    # 2. Query and assign role in DB
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role_obj = res.scalar_one()

    query_user = select(User).where(User.username == username).options(selectinload(User.roles))
    res_user = await db.execute(query_user)
    user_obj = res_user.scalar_one()
    if role_obj not in user_obj.roles:
        user_obj.roles.append(role_obj)
    await db.commit()

    # 3. Login user
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# UNIT TESTS (VALIDATOR & PREPROCESSORS)
# ==========================================

async def test_image_validator_magic_bytes():
    # PNG Magic Bytes
    png_bytes = create_test_image("PNG")
    valid, mime = image_validator.verify_magic_bytes(io.BytesIO(png_bytes))
    assert valid is True
    assert mime == "image/png"

    # JPEG Magic Bytes
    jpg_bytes = create_test_image("JPEG")
    valid, mime = image_validator.verify_magic_bytes(io.BytesIO(jpg_bytes))
    assert valid is True
    assert mime == "image/jpeg"

    # Invalid Magic Bytes (Spoofing)
    bad_bytes = b"bad file headers of some script or executable code"
    valid, mime = image_validator.verify_magic_bytes(io.BytesIO(bad_bytes))
    assert valid is False
    assert mime is None


async def test_integrity_checker():
    png_bytes = create_test_image("PNG")
    valid, err = integrity_checker.verify_pixel_integrity(io.BytesIO(png_bytes))
    assert valid is True
    assert err is None

    bad_bytes = b"bad corrupt binary image payload"
    valid, err = integrity_checker.verify_pixel_integrity(io.BytesIO(bad_bytes))
    assert valid is False
    assert "corrupted" in err.lower()


async def test_image_preprocessor_exif():
    png_bytes = create_test_image("PNG")
    exif = image_preprocessor.extract_exif(png_bytes)
    assert exif["width"] == 200
    assert exif["height"] == 200
    assert exif["camera_model"] is None


async def test_image_transformer_normalize():
    png_bytes = create_test_image("PNG", size=(10, 10))
    flat_pixels = image_transformer.normalize_pixels(png_bytes, target_size=(5, 5))
    assert len(flat_pixels) == 5 * 5 * 3  # RGB
    # Since background was red, first index should be 1.0 (R) and others 0.0
    assert flat_pixels[0] == 1.0
    assert flat_pixels[1] == 0.0
    assert flat_pixels[2] == 0.0


async def test_image_optimizer():
    png_bytes = create_test_image("PNG", size=(100, 100))
    opt_bytes = await image_optimizer.optimize_and_compress(png_bytes, quality=50, target_format="WEBP")
    assert len(opt_bytes) < len(png_bytes)  # Compressed WEBP should be smaller than PNG


async def test_cache_manager():
    cache_manager.clear()
    assert cache_manager.get("key") is None
    cache_manager.set("key", "val", ttl_seconds=1)
    assert cache_manager.get("key") == "val"
    import asyncio
    await asyncio.sleep(1.1)
    assert cache_manager.get("key") is None


# ==========================================
# API INTEGRATION TESTS
# ==========================================

async def test_single_image_upload_and_rbac(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    viewer_headers = await get_auth_headers(client, "Viewer", db)

    image_bytes = create_test_image("PNG")

    # 1. Try uploading as viewer (Should Fail with 403 Forbidden)
    fail_res = await client.post(
        "/api/v1/images/upload",
        headers=viewer_headers,
        data={"source": "manual"},
        files={"file": ("test_img.png", image_bytes, "image/png")}
    )
    assert fail_res.status_code == 403

    # 2. Upload as officer (Should Succeed)
    ok_res = await client.post(
        "/api/v1/images/upload",
        headers=officer_headers,
        data={"source": "manual"},
        files={"file": ("test_img.png", image_bytes, "image/png")}
    )
    assert ok_res.status_code == 201
    img_data = ok_res.json()
    assert img_data["filename"] == "test_img.png"
    assert img_data["upload_source"] == "manual"
    assert img_data["status"] == "active"
    assert img_data["retrieval_url"] is not None

    # 3. Retrieve list
    list_res = await client.get("/api/v1/images", headers=officer_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


async def test_bulk_image_upload(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    img1 = create_test_image("PNG", color="green")
    img2 = create_test_image("PNG", color="yellow")

    res = await client.post(
        "/api/v1/images/bulk-upload",
        headers=officer_headers,
        data={"source": "drone"},
        files=[
            ("files", ("img1.png", img1, "image/png")),
            ("files", ("img2.png", img2, "image/png"))
        ]
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total"] == 2
    assert data["success_count"] == 2


async def test_zip_image_upload_background(client: AsyncClient, db: AsyncSession, monkeypatch):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        zipf.writestr("fire/img1.png", create_test_image(color="orange"))
        zipf.writestr("non_fire/img2.png", create_test_image(color="blue"))
    zip_bytes = zip_buffer.getvalue()

    # Intercept BackgroundTasks.add_task
    from fastapi import BackgroundTasks
    captured_tasks = []
    def mock_add_task(self, func, *args, **kwargs):
        captured_tasks.append((func, args, kwargs))
    
    monkeypatch.setattr(BackgroundTasks, "add_task", mock_add_task)

    # Intercept SessionLocal in upload_processor to reuse the test's transactional db session
    import app.services.upload_processor as up_proc
    class SessionContext:
        async def __aenter__(self):
            return db
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    monkeypatch.setattr(up_proc, "SessionLocal", SessionContext)

    res = await client.post(
        "/api/v1/images/upload-zip",
        headers=officer_headers,
        data={"source": "satellite"},
        files={"file": ("archive.zip", zip_bytes, "application/zip")}
    )
    assert res.status_code == 202
    assert "task_id" in res.json()

    # Manually execute the background task synchronously within the active test database session
    assert len(captured_tasks) == 1
    func, args, kwargs = captured_tasks[0]
    await func(*args, **kwargs)

    # Verify images were processed and created
    images = await image_repository.list_images(db, limit=10)
    assert len(images) >= 2


async def test_image_advanced_search_and_stats(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)

    # Upload an image to search for
    image_bytes = create_test_image("PNG")
    upload_res = await client.post(
        "/api/v1/images/upload",
        headers=officer_headers,
        data={"source": "cctv"},
        files={"file": ("search_img.png", image_bytes, "image/png")}
    )
    assert upload_res.status_code == 201
    img_id = upload_res.json()["id"]

    # Retrieve stats
    stats_res = await client.get("/api/v1/images/statistics", headers=officer_headers)
    assert stats_res.status_code == 200
    assert stats_res.json()["total_count"] >= 1
    assert "cctv" in stats_res.json()["source_breakdown"]

    # Advanced Search
    search_res = await client.get(
        "/api/v1/images/search",
        headers=officer_headers,
        params={"source": "cctv", "min_width": 100, "max_width": 500}
    )
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert len(items) >= 1
    assert items[0]["id"] == img_id


async def test_image_lifecycle_management(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    admin_headers = await get_auth_headers(client, "Super Admin", db)

    # 1. Upload image
    img_bytes = create_test_image("PNG")
    up_res = await client.post(
        "/api/v1/images/upload",
        headers=officer_headers,
        data={"source": "manual"},
        files={"file": ("lifecycle_img.png", img_bytes, "image/png")}
    )
    img_id = up_res.json()["id"]

    # 2. Archive image using lifecycle service directly
    from app.services.image_lifecycle_service import image_lifecycle_service
    # Fetch admin user to use as lifecycle executor
    query = select(User).where(User.username == "admin")
    res = await db.execute(query)
    admin_user = res.scalar_one_or_none()
    if not admin_user:
        # seeding admin if not found in db transaction
        admin_user = User(email="t_admin@forest.org", username="t_admin", hashed_password="pwd", is_active=True)
        db.add(admin_user)
        await db.flush()

    archived_img = await image_lifecycle_service.archive_image(db, uuid.UUID(img_id), admin_user.id)
    assert archived_img.status == "archived"

    # Check that paths now start with 'archive/'
    primary_loc = await image_storage_location_repository.get_primary_location(db, uuid.UUID(img_id))
    assert primary_loc.file_key_or_path.startswith("archive/")

    # 3. Restore image
    restored_img = await image_lifecycle_service.restore_image(db, uuid.UUID(img_id), admin_user.id)
    assert restored_img.status == "active"
    primary_loc_restored = await image_storage_location_repository.get_primary_location(db, uuid.UUID(img_id))
    assert not primary_loc_restored.file_key_or_path.startswith("archive/")

    # 4. Soft Delete via DELETE Endpoint (Should Fail as Forest Officer)
    del_fail = await client.delete(f"/api/v1/images/{img_id}", headers=officer_headers)
    assert del_fail.status_code == 403

    # 5. Soft Delete via DELETE Endpoint (Should Succeed as Super Admin)
    del_res = await client.delete(f"/api/v1/images/{img_id}", headers=admin_headers)
    assert del_res.status_code == 204

    # Verify soft-deleted image is flagged in DB
    re_query = select(ImageModel).where(ImageModel.id == uuid.UUID(img_id))
    re_res = await db.execute(re_query)
    deleted_img = re_res.scalar_one()
    assert deleted_img.deleted_at is not None

    # 6. Permanent Delete via service
    purged = await image_lifecycle_service.permanent_delete_image(db, uuid.UUID(img_id), admin_user.id)
    assert purged is True

    # Verify totally removed from DB
    re_query2 = select(ImageModel).where(ImageModel.id == uuid.UUID(img_id))
    re_res2 = await db.execute(re_query2)
    assert re_res2.scalar_one_or_none() is None


# ==========================================
# OPTIMIZER & STORAGE INTEGRITY TESTS
# ==========================================

async def test_storage_optimizer_deduplication(db: AsyncSession):
    # Upload first
    file_bytes = create_test_image("PNG", color="black")
    md5 = "test_black_image_md5_hash"
    
    # Manually populate an image
    img = ImageModel(filename="black.png", original_filename="black.png", size_bytes=len(file_bytes), md5_hash=md5, owner_id=uuid.uuid4(), upload_source="manual")
    db.add(img)
    await db.flush()
    
    loc = ImageStorageLocation(image_id=img.id, provider="local", bucket_or_container="storage", file_key_or_path="images/black.png", is_primary=True)
    db.add(loc)
    await db.flush()

    # Check shared location for same hash
    shared_path = await storage_optimizer.get_shared_location_if_duplicate(db, md5)
    assert shared_path == "images/black.png"


async def test_storage_migration(db: AsyncSession):
    # Setup image
    file_bytes = create_test_image("PNG")
    md5 = "migration_test_image_md5"
    img = ImageModel(filename="mig.png", original_filename="mig.png", size_bytes=len(file_bytes), md5_hash=md5, owner_id=uuid.uuid4(), upload_source="manual")
    db.add(img)
    await db.flush()

    loc = ImageStorageLocation(image_id=img.id, provider="local", bucket_or_container="storage", file_key_or_path="images/mig.png", is_primary=True)
    db.add(loc)
    await db.flush()

    # Save to local storage mock
    await storage_service.save_file(file_bytes, "images/mig.png")

    # Migrate to simulated S3 bucket
    mig_report = await file_storage_manager.migrate_image(
        db=db,
        image_id=img.id,
        target_provider="s3",
        target_bucket_or_container="migrated-s3-bucket"
    )
    assert mig_report["status"] == "success"
    assert mig_report["new_provider"] == "s3"
    assert "images/" in mig_report["new_path"]

    # Verify location updated in DB
    new_loc = await image_storage_location_repository.get_primary_location(db, img.id)
    assert new_loc.provider == "s3"
    assert new_loc.bucket_or_container == "migrated-s3-bucket"
