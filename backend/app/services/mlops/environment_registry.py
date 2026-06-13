import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import Environment
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.services.mlops.environment_manager import environment_manager


class EnvironmentRegistry:
    @staticmethod
    async def get_environment(db: AsyncSession, env_id: uuid.UUID) -> Optional[Environment]:
        query = select(Environment).where(
            and_(Environment.id == env_id, Environment.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_environment_by_name(db: AsyncSession, name: str) -> Optional[Environment]:
        clean_name = name.strip().lower()
        query = select(Environment).where(
            and_(Environment.name == clean_name, Environment.deleted_at.is_(None))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_environment(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        config_data: Optional[Dict[str, Any]] = None
    ) -> Environment:
        clean_name = name.strip().lower()
        if not clean_name:
            raise ValidationException("Environment name cannot be empty.")

        existing = await EnvironmentRegistry.get_environment_by_name(db, clean_name)
        if existing:
            raise ValidationException(f"Environment with name '{clean_name}' is already registered.")

        # Validate configuration if config_data is provided
        if config_data:
            is_valid, err_msg = environment_manager.validate_configuration(config_data, config_schema)
            if not is_valid:
                raise ValidationException(f"Failed configuration schema validation: {err_msg}")

        env = Environment(
            name=clean_name,
            description=description,
            config_schema=config_schema or {},
            config_data=config_data or {},
            status="healthy"
        )
        db.add(env)
        await db.commit()
        await db.refresh(env)
        return env

    @staticmethod
    async def list_environments(db: AsyncSession, skip: int = 0, limit: int = 20) -> Tuple[List[Environment], int]:
        query = select(Environment).where(Environment.deleted_at.is_(None)).offset(skip).limit(limit)
        count_query = select(func.count()).select_from(Environment).where(Environment.deleted_at.is_(None))

        res = await db.execute(query)
        envs = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return envs, total

    @staticmethod
    async def update_environment_status(db: AsyncSession, env_id: uuid.UUID, status: str) -> Environment:
        env = await EnvironmentRegistry.get_environment(db, env_id)
        if not env:
            raise EntityNotFoundException(f"Environment '{env_id}' not found.")

        env.status = status.strip().lower()
        await db.commit()
        await db.refresh(env)
        return env

    @staticmethod
    async def update_environment_release(db: AsyncSession, env_id: uuid.UUID, release_id: Optional[uuid.UUID]) -> Environment:
        env = await EnvironmentRegistry.get_environment(db, env_id)
        if not env:
            raise EntityNotFoundException(f"Environment '{env_id}' not found.")

        env.current_release_id = release_id
        await db.commit()
        await db.refresh(env)
        return env


environment_registry = EnvironmentRegistry()
