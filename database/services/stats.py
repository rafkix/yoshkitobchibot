from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def count_total_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.user_id)))
    return int(result.scalar_one() or 0)


async def count_registered_users(session: AsyncSession) -> int:
    """Users who completed registration."""
    result = await session.execute(
        select(func.count(User.user_id)).where(
            User.is_registered.is_(True),
        )
    )
    return int(result.scalar_one() or 0)


async def count_unregistered_users(session: AsyncSession) -> int:
    """Users who started the bot but never finished registration."""
    result = await session.execute(
        select(func.count(User.user_id)).where(
            User.is_registered.is_(False),
        )
    )
    return int(result.scalar_one() or 0)


async def count_new_users_since(session: AsyncSession, days: int) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.user_id)).where(User.created_at >= threshold)
    )
    return int(result.scalar_one() or 0)


async def count_new_registered_users_since(session: AsyncSession, days: int) -> int:
    """Registered users who joined within the last N days."""
    threshold = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(func.count(User.user_id)).where(
            User.created_at >= threshold,
            User.is_registered.is_(True),
        )
    )
    return int(result.scalar_one() or 0)