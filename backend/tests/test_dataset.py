import io
import pytest
import uuid
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset, DatasetCategory, DatasetLabel, DatasetVersion, DatasetFile


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def seed_dataset_data(db: AsyncSession):
    from app.services.dataset_service import dataset_service
    await dataset_service.seed_categories_and_labels(db)
    await db.commit()


def create_dummy_image(size=(200, 200), color="red") -> bytes:
    """Helper to generate valid PNG bytes for validator checks."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def get_auth_headers(client: AsyncClient, role_name: str, db: AsyncSession) -> dict:
    """Helper to register and login a user with a specific seeded role."""
    # Build unique username
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


async def test_dataset_categories_and_labels_seeded(db: AsyncSession):
    # Verify categories exist
    cat_query = select(DatasetCategory)
    res = await db.execute(cat_query)
    categories = {c.name for c in res.scalars().all()}
    assert "Fire Images" in categories
    assert "Training Datasets" in categories

    # Verify labels exist
    lbl_query = select(DatasetLabel)
    res = await db.execute(lbl_query)
    labels = {l.name for l in res.scalars().all()}
    assert "Fire" in labels
    assert "Smoke" in labels


async def test_dataset_lifecycle_and_rbac(client: AsyncClient, db: AsyncSession):
    # Get auth tokens
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    viewer_headers = await get_auth_headers(client, "Viewer", db)
    admin_headers = await get_auth_headers(client, "Super Admin", db)

    # 1. Retrieve categories
    cat_res = await client.get("/api/v1/datasets/categories", headers=officer_headers)
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert len(categories) > 0
    category_id = categories[0]["id"]

    # 2. Try creating dataset as Viewer (Should Fail)
    view_fail = await client.post(
        "/api/v1/datasets",
        headers=viewer_headers,
        json={
            "name": "Failed Dataset",
            "description": "Fail",
            "category_id": category_id
        }
    )
    assert view_fail.status_code == 403

    # 3. Create dataset as Officer (Should Succeed)
    dataset_name = f"Test Dataset {uuid.uuid4().hex[:6]}"
    create_res = await client.post(
        "/api/v1/datasets",
        headers=officer_headers,
        json={
            "name": dataset_name,
            "description": "In-depth testing dataset.",
            "category_id": category_id,
            "tags": "fire,test,spatial"
        }
    )
    assert create_res.status_code == 201
    dataset_data = create_res.json()
    assert dataset_data["name"] == dataset_name
    dataset_id = dataset_data["id"]

    # 4. List datasets
    list_res = await client.get("/api/v1/datasets", headers=viewer_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 5. Update dataset as Officer
    update_res = await client.put(
        f"/api/v1/datasets/{dataset_id}",
        headers=officer_headers,
        json={
            "name": dataset_name + " Updated",
            "description": "Updated description"
        }
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated description"

    # 6. Delete dataset as Viewer (Should Fail)
    del_fail = await client.delete(f"/api/v1/datasets/{dataset_id}", headers=officer_headers)
    assert del_fail.status_code == 403  # Requires manage_platform_settings (Super Admin)

    # 7. Delete dataset as Admin (Should Succeed)
    del_ok = await client.delete(f"/api/v1/datasets/{dataset_id}", headers=admin_headers)
    assert del_ok.status_code == 204


async def test_dataset_upload_and_validation(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)

    # Resolve a category
    cat_query = select(DatasetCategory).limit(1)
    res = await db.execute(cat_query)
    cat = res.scalar_one()

    # Create dataset
    ds = Dataset(name=f"Upload ds {uuid.uuid4().hex[:6]}", category_id=cat.id, user_id=uuid.uuid4(), status="active")
    db.add(ds)
    await db.commit()

    # Get Labels
    lbl_query = select(DatasetLabel).limit(1)
    res_lbl = await db.execute(lbl_query)
    lbl = res_lbl.scalar_one()

    # Prepare dummy image
    image_bytes = create_dummy_image(size=(150, 150), color="blue")
    
    # 1. Single File Upload
    response = await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={
            "dataset_id": str(ds.id),
            "label_id": str(lbl.id)
        },
        files={"file": ("test_img.png", image_bytes, "image/png")}
    )
    assert response.status_code == 201
    file_data = response.json()
    assert file_data["filename"] == "test_img.png"
    assert file_data["label_id"] == str(lbl.id)

    # 2. Duplicate Check Validation (Should Fail)
    dup_res = await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={"dataset_id": str(ds.id)},
        files={"file": ("test_img.png", image_bytes, "image/png")}
    )
    assert dup_res.status_code == 422
    assert "duplicate" in dup_res.json()["error"]["message"].lower()

    # 3. Bad Format Check Validation (Should Fail)
    bad_res = await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={"dataset_id": str(ds.id)},
        files={"file": ("malicious.txt", b"import os; os.system('malicious')", "text/plain")}
    )
    assert bad_res.status_code == 422


async def test_dataset_versioning_and_rollback(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    analyst_headers = await get_auth_headers(client, "Research Analyst", db)

    # Seed Category
    cat_query = select(DatasetCategory).limit(1)
    res = await db.execute(cat_query)
    cat = res.scalar_one()

    # Create Dataset
    ds = Dataset(name=f"Version ds {uuid.uuid4().hex[:6]}", category_id=cat.id, user_id=uuid.uuid4(), status="active")
    db.add(ds)
    await db.commit()

    # Upload first file
    img1 = create_dummy_image(color="green")
    await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={"dataset_id": str(ds.id)},
        files={"file": ("img1.png", img1, "image/png")}
    )

    # 1. Create Version Snapshot v1.0.0
    ver_res = await client.post(
        f"/api/v1/datasets/{ds.id}/versions",
        headers=analyst_headers,
        json={
            "version_str": "v1.0.0",
            "description": "Baseline v1"
        }
    )
    assert ver_res.status_code == 201
    ver_data = ver_res.json()
    assert ver_data["version_str"] == "v1.0.0"
    assert ver_data["file_count"] == 1

    # Upload second file (modifying the dataset state)
    img2 = create_dummy_image(color="yellow")
    await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={"dataset_id": str(ds.id)},
        files={"file": ("img2.png", img2, "image/png")}
    )

    # Check file list (now contains 2 files)
    files_res = await client.get(f"/api/v1/datasets/{ds.id}/files", headers=officer_headers)
    assert files_res.status_code == 200
    assert files_res.json()["total"] == 2

    # 2. Rollback to v1.0.0
    rollback_res = await client.post(
        f"/api/v1/datasets/{ds.id}/rollback",
        headers=analyst_headers,
        json={"version_str": "v1.0.0"}
    )
    assert rollback_res.status_code == 200
    assert rollback_res.json()["restored_files"] == 1

    # Check file list again (should only contain 1 restored file)
    files_res_2 = await client.get(f"/api/v1/datasets/{ds.id}/files", headers=officer_headers)
    assert files_res_2.status_code == 200
    assert files_res_2.json()["total"] == 1
    assert files_res_2.json()["items"][0]["filename"] == "img1.png"


async def test_bulk_label_mapping(client: AsyncClient, db: AsyncSession):
    officer_headers = await get_auth_headers(client, "Forest Officer", db)
    analyst_headers = await get_auth_headers(client, "Research Analyst", db)

    # Setup Dataset
    cat_query = select(DatasetCategory).limit(1)
    res = await db.execute(cat_query)
    cat = res.scalar_one()

    ds = Dataset(name=f"Label ds {uuid.uuid4().hex[:6]}", category_id=cat.id, user_id=uuid.uuid4(), status="active")
    db.add(ds)
    await db.commit()

    # Upload File
    img = create_dummy_image()
    up_res = await client.post(
        "/api/v1/datasets/upload",
        headers=officer_headers,
        data={"dataset_id": str(ds.id)},
        files={"file": ("labeled_img.png", img, "image/png")}
    )
    file_id = up_res.json()["id"]

    # Get Target Label (Fire)
    lbl_query = select(DatasetLabel).where(DatasetLabel.name == "Fire")
    res_lbl = await db.execute(lbl_query)
    lbl = res_lbl.scalar_one()

    # 1. Bulk assign label
    lbl_assign_res = await client.post(
        f"/api/v1/datasets/{ds.id}/labels",
        headers=analyst_headers,
        json={
            "file_ids": [file_id],
            "label_id": str(lbl.id)
        }
    )
    assert lbl_assign_res.status_code == 200
    assert lbl_assign_res.json()["updated_count"] == 1

    # 2. Check label is updated in file registry
    files_res = await client.get(f"/api/v1/datasets/{ds.id}/files", headers=officer_headers)
    assert files_res.json()["items"][0]["label_id"] == str(lbl.id)
