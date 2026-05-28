from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def count_total_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.user_id)))
    return int(result.scalar_one() or 0)


async def count_active_users(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(User.user_id)).where(
            User.is_active.is_(True),
            User.is_blocked.is_(False),
        )
    )
    return int(result.scalar_one() or 0)


async def count_left_users(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(User.user_id)).where(
            (User.is_active.is_(False)) | (User.is_blocked.is_(True))
        )
    )
    return int(result.scalar_one() or 0)


async def count_new_users_since(session: AsyncSession, days: int) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.user_id)).where(User.created_at >= threshold)
    )
    return int(result.scalar_one() or 0)


async def count_active_users_since(session: AsyncSession, days: int) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.user_id)).where(
            User.last_activity_at.is_not(None),
            User.last_activity_at >= threshold,
            User.is_blocked.is_(False),
        )
    )
    return int(result.scalar_one() or 0)