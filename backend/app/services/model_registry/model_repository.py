import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import (
    RegisteredModel,
    ModelVersion,
    ModelArtifact,
    ModelMetadata,
    ModelDeployment,
    ModelApproval,
    ModelLifecycleEvent,
    ModelAuditLog,
)


class ModelRepository:
    # --- Registered Model ---
    @staticmethod
    async def get_model(db: AsyncSession, model_id: uuid.UUID) -> Optional[RegisteredModel]:
        query = select(RegisteredModel).where(and_(RegisteredModel.id == model_id, RegisteredModel.deleted_at.is_(None)))
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_model_by_name(db: AsyncSession, name: str) -> Optional[RegisteredModel]:
        query = select(RegisteredModel).where(and_(RegisteredModel.name == name, RegisteredModel.deleted_at.is_(None)))
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_model(
        db: AsyncSession, name: str, description: Optional[str] = None, created_by: Optional[uuid.UUID] = None
    ) -> RegisteredModel:
        model = RegisteredModel(name=name, description=description, created_by=created_by)
        db.add(model)
        await db.commit()
        await db.refresh(model)
        return model

    @staticmethod
    async def list_models(db: AsyncSession, skip: int = 0, limit: int = 20) -> Tuple[List[RegisteredModel], int]:
        query = select(RegisteredModel).where(RegisteredModel.deleted_at.is_(None)).offset(skip).limit(limit)
        count_query = select(func.count()).select_from(RegisteredModel).where(RegisteredModel.deleted_at.is_(None))

        res = await db.execute(query)
        models = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return models, total

    # --- Model Version ---
    @staticmethod
    async def get_version(db: AsyncSession, version_id: uuid.UUID) -> Optional[ModelVersion]:
        from sqlalchemy.orm import selectinload

        query = (
            select(ModelVersion)
            .options(selectinload(ModelVersion.artifacts))
            .where(and_(ModelVersion.id == version_id, ModelVersion.deleted_at.is_(None)))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_version_by_number(db: AsyncSession, model_id: uuid.UUID, version_str: str) -> Optional[ModelVersion]:
        query = select(ModelVersion).where(
            and_(ModelVersion.model_id == model_id, ModelVersion.version == version_str, ModelVersion.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_latest_version(db: AsyncSession, model_id: uuid.UUID) -> Optional[ModelVersion]:
        query = (
            select(ModelVersion)
            .where(and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None)))
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_version(
        db: AsyncSession,
        model_id: uuid.UUID,
        version_str: str,
        training_run_id: Optional[uuid.UUID] = None,
        checkpoint_id: Optional[uuid.UUID] = None,
        status: str = "Draft",
        created_by: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        release_notes: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> ModelVersion:
        version = ModelVersion(
            model_id=model_id,
            version=version_str,
            training_run_id=training_run_id,
            checkpoint_id=checkpoint_id,
            status=status,
            created_by=created_by,
            description=description,
            release_notes=release_notes,
            metrics=metrics,
            hyperparameters=hyperparameters,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version

    @staticmethod
    async def list_versions(
        db: AsyncSession, model_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> Tuple[List[ModelVersion], int]:
        query = (
            select(ModelVersion)
            .where(and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None)))
            .order_by(ModelVersion.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        count_query = (
            select(func.count())
            .select_from(ModelVersion)
            .where(and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None)))
        )

        res = await db.execute(query)
        versions = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return versions, total

    # --- Model Artifact ---
    @staticmethod
    async def create_artifact(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        name: str,
        artifact_type: str,
        uri: str,
        file_size: Optional[int] = None,
        checksum: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ModelArtifact:
        artifact = ModelArtifact(
            model_version_id=model_version_id,
            name=name,
            artifact_type=artifact_type,
            uri=uri,
            file_size=file_size,
            checksum=checksum,
            created_by=created_by,
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        return artifact

    # --- Model Metadata ---
    @staticmethod
    async def create_metadata(
        db: AsyncSession, model_version_id: uuid.UUID, key: str, value: str, value_type: str = "string"
    ) -> ModelMetadata:
        meta = ModelMetadata(model_version_id=model_version_id, key=key, value=value, value_type=value_type)
        db.add(meta)
        await db.commit()
        await db.refresh(meta)
        return meta

    # --- Model Deployment ---
    @staticmethod
    async def get_active_deployment(db: AsyncSession, model_id: uuid.UUID, environment: str) -> Optional[ModelDeployment]:
        # Subquery to resolve version IDs belonging to model_id
        version_ids_query = select(ModelVersion.id).where(
            and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None))
        )
        res_vids = await db.execute(version_ids_query)
        vids = list(res_vids.scalars().all())
        if not vids:
            return None

        query = (
            select(ModelDeployment)
            .where(
                and_(
                    ModelDeployment.model_version_id.in_(vids),
                    ModelDeployment.environment == environment.lower().strip(),
                    ModelDeployment.status == "active",
                    ModelDeployment.deleted_at.is_(None),
                )
            )
            .order_by(ModelDeployment.deployed_at.desc())
            .limit(1)
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_deployment(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        environment: str,
        status: str = "active",
        deployed_by: Optional[uuid.UUID] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ModelDeployment:
        # First, deactivate any active deployments in the same environment for the same model family
        version = await ModelRepository.get_version(db, model_version_id)
        if version:
            active_deploys_query = select(ModelDeployment).where(
                and_(
                    ModelDeployment.environment == environment.lower().strip(),
                    ModelDeployment.status == "active",
                    ModelDeployment.deleted_at.is_(None),
                )
            )
            res_active = await db.execute(active_deploys_query)
            active_deploys = res_active.scalars().all()
            for d in active_deploys:
                # Check if it belongs to the same model family
                d_version = await ModelRepository.get_version(db, d.model_version_id)
                if d_version and d_version.model_id == version.model_id:
                    d.status = "inactive"
                    d.undeployed_at = datetime.utcnow()
            await db.commit()

        deployment = ModelDeployment(
            model_version_id=model_version_id,
            environment=environment.lower().strip(),
            status=status,
            deployed_by=deployed_by,
            metrics=metrics,
        )
        db.add(deployment)
        await db.commit()
        await db.refresh(deployment)
        return deployment

    @staticmethod
    async def get_previous_deployment(db: AsyncSession, model_id: uuid.UUID, environment: str) -> Optional[ModelDeployment]:
        version_ids_query = select(ModelVersion.id).where(
            and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None))
        )
        res_vids = await db.execute(version_ids_query)
        vids = list(res_vids.scalars().all())
        if not vids:
            return None

        # Previous deployment is inactive but wasn't failed, or is just the next newest deployment in line
        query = (
            select(ModelDeployment)
            .where(
                and_(
                    ModelDeployment.model_version_id.in_(vids),
                    ModelDeployment.environment == environment.lower().strip(),
                    ModelDeployment.status != "active",
                    ModelDeployment.deleted_at.is_(None),
                )
            )
            .order_by(ModelDeployment.deployed_at.desc())
            .limit(1)
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    # --- Model Approval ---
    @staticmethod
    async def get_approval(db: AsyncSession, approval_id: uuid.UUID) -> Optional[ModelApproval]:
        query = select(ModelApproval).where(and_(ModelApproval.id == approval_id, ModelApproval.deleted_at.is_(None)))
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_approval(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        requested_by: uuid.UUID,
        target_stage: str,
        request_notes: Optional[str] = None,
    ) -> ModelApproval:
        approval = ModelApproval(
            model_version_id=model_version_id,
            requested_by=requested_by,
            target_stage=target_stage,
            request_notes=request_notes,
            status="pending",
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval

    # --- Model Lifecycle Event ---
    @staticmethod
    async def create_lifecycle_event(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        from_state: str,
        to_state: str,
        triggered_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> ModelLifecycleEvent:
        event = ModelLifecycleEvent(
            model_version_id=model_version_id, from_state=from_state, to_state=to_state, triggered_by=triggered_by, notes=notes
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    # --- Model Audit Log ---
    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        action: str,
        performed_by: uuid.UUID,
        model_version_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
    ) -> ModelAuditLog:
        log = ModelAuditLog(
            action=action,
            performed_by=performed_by,
            model_version_id=model_version_id,
            details=details or {},
            client_ip=client_ip,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log


model_repository = ModelRepository()
