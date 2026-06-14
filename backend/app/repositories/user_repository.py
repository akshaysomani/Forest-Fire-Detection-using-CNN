from typing import Any
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.user import User
from app.models.role import Role


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str, include_deleted: bool = False) -> User | None:
        query = select(User).where(User.email == email)
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        # Pre-load roles
        query = query.options(selectinload(User.roles))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str, include_deleted: bool = False) -> User | None:
        query = select(User).where(User.username == username)
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        # Pre-load roles
        query = query.options(selectinload(User.roles))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, db: AsyncSession, identifier: str, include_deleted: bool = False) -> User | None:
        query = select(User).where(or_(User.email == identifier, User.username == identifier))
        if not include_deleted:
            query = query.where(User.deleted_at.is_(None))
        query = query.options(selectinload(User.roles))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_with_roles_and_permissions(self, db: AsyncSession, user_id: Any) -> User | None:
        query = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        # Deeply load roles and permissions
        query = query.options(selectinload(User.roles).selectinload(Role.permissions))
        result = await db.execute(query)
        return result.scalar_one_or_none()


# Global user repository instance
user_repository = UserRepository()
