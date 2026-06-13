import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import Release
from app.core.exceptions import ValidationException, EntityNotFoundException


class ReleaseRegistry:
    @staticmethod
    async def get_release(db: AsyncSession, release_id: uuid.UUID) -> Optional[Release]:
        query = select(Release).where(
            and_(Release.id == release_id, Release.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_release_by_version(db: AsyncSession, version: str) -> Optional[Release]:
        clean_ver = version.strip().lower()
        query = select(Release).where(
            and_(Release.version == clean_ver, Release.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_release(
        db: AsyncSession,
        version: str,
        description: Optional[str] = None,
        model_version_id: Optional[uuid.UUID] = None,
        release_notes: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> Release:
        clean_ver = version.strip().lower()
        if not clean_ver:
            raise ValidationException("Release version cannot be empty.")

        existing = await ReleaseRegistry.get_release_by_version(db, clean_ver)
        if existing:
            raise ValidationException(f"Release version '{clean_ver}' is already registered.")

        # Ensure correct system creator UUID
        creator_id = created_by or uuid.UUID(int=0)

        release = Release(
            version=clean_ver,
            description=description,
            model_version_id=model_version_id,
            status="active",
            created_by=creator_id,
            release_notes=release_notes
        )
        db.add(release)
        await db.commit()
        await db.refresh(release)
        return release

    @staticmethod
    async def list_releases(db: AsyncSession, skip: int = 0, limit: int = 20) -> Tuple[List[Release], int]:
        query = select(Release).where(Release.deleted_at.is_(None)).order_by(Release.created_at.desc()).offset(skip).limit(limit)
        count_query = select(func.count()).select_from(Release).where(Release.deleted_at.is_(None))

        res = await db.execute(query)
        releases = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return releases, total

    @staticmethod
    async def update_release_status(db: AsyncSession, release_id: uuid.UUID, status: str) -> Release:
        release = await ReleaseRegistry.get_release(db, release_id)
        if not release:
            raise EntityNotFoundException(f"Release '{release_id}' not found.")

        release.status = status.strip().lower()
        await db.commit()
        await db.refresh(release)
        return release


release_registry = ReleaseRegistry()
