import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage_service import storage_service
from app.repositories.image_repository import (
    image_repository,
    image_storage_location_repository,
)


class CleanupService:
    async def delete_image_files(self, db: AsyncSession, image_id: uuid.UUID) -> int:
        """
        Delete all physical files associated with an image (primary file + all preprocessed versions).
        Returns count of deleted files.
        """
        locations = await image_storage_location_repository.list_locations(db, image_id)
        deleted_count = 0

        for loc in locations:
            try:
                exists = await storage_service.exists(loc.file_key_or_path)
                if exists:
                    await storage_service.delete_file(loc.file_key_or_path)
                    deleted_count += 1
            except Exception:
                # Log error but continue sweeping remaining files
                pass

        return deleted_count

    async def purge_soft_deleted_images(self, db: AsyncSession, older_than_days: int = 30) -> int:
        """
        Scan database for soft-deleted images older than older_than_days,
        physically delete their storage assets, and delete DB records permanently.
        """
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        # Query images soft-deleted before cutoff date
        query = select(image_repository.model).where(
            and_(
                image_repository.model.deleted_at.is_not(None),
                image_repository.model.deleted_at <= cutoff_date
            )
        )
        res = await db.execute(query)
        stale_images = res.scalars().all()

        purged_count = 0
        for img in stale_images:
            # Delete physical files
            await self.delete_image_files(db, img.id)
            # Permanent delete from DB
            await image_repository.delete(db, img.id)
            purged_count += 1

        return purged_count


cleanup_service = CleanupService()
