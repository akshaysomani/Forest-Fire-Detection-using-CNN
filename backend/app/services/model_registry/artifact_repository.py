import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import ModelArtifact


class ArtifactRepository:
    @staticmethod
    async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> Optional[ModelArtifact]:
        query = select(ModelArtifact).where(
            and_(ModelArtifact.id == artifact_id, ModelArtifact.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_artifacts_for_version(db: AsyncSession, model_version_id: uuid.UUID) -> List[ModelArtifact]:
        query = select(ModelArtifact).where(
            and_(
                ModelArtifact.model_version_id == model_version_id,
                ModelArtifact.deleted_at.is_(None)
            )
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def create_artifact(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        name: str,
        artifact_type: str,
        uri: str,
        file_size: Optional[int] = None,
        checksum: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> ModelArtifact:
        artifact = ModelArtifact(
            model_version_id=model_version_id,
            name=name,
            artifact_type=artifact_type,
            uri=uri,
            file_size=file_size,
            checksum=checksum,
            created_by=created_by
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        return artifact

    @staticmethod
    async def soft_delete_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> bool:
        query = select(ModelArtifact).where(
            and_(ModelArtifact.id == artifact_id, ModelArtifact.deleted_at.is_(None))
        )
        res = await db.execute(query)
        artifact = res.scalar_one_or_none()
        if not artifact:
            return False
        
        from datetime import datetime
        artifact.deleted_at = datetime.utcnow()
        await db.commit()
        return True


artifact_repository = ArtifactRepository()
