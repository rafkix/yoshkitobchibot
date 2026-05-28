from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Channel, ChannelJoin


async def get_channel_join(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> ChannelJoin | None:
    result = await session.execute(
        select(ChannelJoin).where(
            ChannelJoin.user_id == user_id,
            ChannelJoin.channel_id == channel_id,
        )
    )
    return result.scalar_one_or_none()


async def get_active_channel_join(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> ChannelJoin | None:
    result = await session.execute(
        select(ChannelJoin).where(
            ChannelJoin.user_id == user_id,
            ChannelJoin.channel_id == channel_id,
            ChannelJoin.is_joined.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_channel_by_telegram_chat_id(
    session: AsyncSession,
    telegram_chat_id: int,
) -> Channel | None:
    result = await session.execute(
        select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
    )
    return result.scalar_one_or_none()


async def mark_channel_join_requested(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> ChannelJoin | None:
    """
    User private/request kanalga join request yubordi.
    Hali approved emas, shuning uchun is_joined=False bo‘lib turadi.
    """
    try:
        existing_join = await get_channel_join(session, user_id, channel_id)

        if existing_join:
            existing_join.is_joined = False
            existing_join.left_at = None
            await session.commit()
            await session.refresh(existing_join)
            return existing_join

        new_join = ChannelJoin(
            user_id=user_id,
            channel_id=channel_id,
            is_joined=True,
            left_at=None,
        )
        session.add(new_join)
        await session.commit()
        await session.refresh(new_join)
        return new_join

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Join request saqlashda xatolik: {e}")
        return None


async def mark_channel_joined(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> ChannelJoin | None:
    """
    User kanal/guruhga haqiqatan qo‘shildi.
    """
    try:
        existing_join = await get_channel_join(session, user_id, channel_id)

        if existing_join:
            existing_join.is_joined = True
            existing_join.left_at = None
            await session.commit()
            await session.refresh(existing_join)
            return existing_join

        new_join = ChannelJoin(
            user_id=user_id,
            channel_id=channel_id,
            is_joined=True,
            left_at=None,
        )
        session.add(new_join)
        await session.commit()
        await session.refresh(new_join)
        return new_join

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ ChannelJoin qo‘shishda xatolik: {e}")
        return None


async def mark_channel_joined_by_chat_id(
    session: AsyncSession,
    user_id: int,
    telegram_chat_id: int,
) -> ChannelJoin | None:
    """
    Telegram chat ID orqali channel topib, userni joined deb belgilaydi.
    Middleware/check handler uchun qulay.
    """
    channel = await get_channel_by_telegram_chat_id(session, telegram_chat_id)
    if not channel:
        return None

    return await mark_channel_joined(
        session=session,
        user_id=user_id,
        channel_id=channel.channel_id,
    )


async def mark_channel_request_by_chat_id(
    session: AsyncSession,
    user_id: int,
    telegram_chat_id: int,
) -> ChannelJoin | None:
    """
    Join request event kelganda telegram_chat_id orqali yozib qo‘yadi.
    """
    channel = await get_channel_by_telegram_chat_id(session, telegram_chat_id)
    if not channel:
        return None

    return await mark_channel_join_requested(
        session=session,
        user_id=user_id,
        channel_id=channel.channel_id,
    )


async def add_channel_join(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> ChannelJoin | None:
    """
    Backward compatibility uchun qoldirildi.
    Eski kod buzilmasin desang, shu mark_channel_joined ga delegate qilsin.
    """
    return await mark_channel_joined(
        session=session,
        user_id=user_id,
        channel_id=channel_id,
    )


async def get_user_channel_joins(
    session: AsyncSession,
    user_id: int,
    active_only: bool = False,
) -> list[ChannelJoin]:
    stmt = (
        select(ChannelJoin)
        .where(ChannelJoin.user_id == user_id)
        .order_by(ChannelJoin.created_at.desc())
    )

    if active_only:
        stmt = stmt.where(ChannelJoin.is_joined.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_channel_users(
    session: AsyncSession,
    channel_id: int,
    active_only: bool = True,
) -> list[ChannelJoin]:
    stmt = (
        select(ChannelJoin)
        .where(ChannelJoin.channel_id == channel_id)
        .order_by(ChannelJoin.created_at.desc())
    )

    if active_only:
        stmt = stmt.where(ChannelJoin.is_joined.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def leave_channel_join(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> bool:
    try:
        join = await get_channel_join(session, user_id, channel_id)
        if not join:
            return False

        if not join.is_joined:
            return True

        join.is_joined = False
        join.left_at = datetime.utcnow()

        await session.commit()
        return True

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ ChannelJoin leave qilishda xatolik: {e}")
        return False


async def delete_channel_join(
    session: AsyncSession,
    user_id: int,
    channel_id: int,
) -> bool:
    try:
        join = await get_channel_join(session, user_id, channel_id)
        if not join:
            return False

        await session.delete(join)
        await session.commit()
        return True

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ ChannelJoin o‘chirishda xatolik: {e}")
        return False


async def count_user_channel_joins(
    session: AsyncSession,
    user_id: int,
    active_only: bool = False,
) -> int:
    stmt = select(func.count(ChannelJoin.id)).where(ChannelJoin.user_id == user_id)

    if active_only:
        stmt = stmt.where(ChannelJoin.is_joined.is_(True))

    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def count_channel_users(
    session: AsyncSession,
    channel_id: int,
    active_only: bool = True,
) -> int:
    stmt = select(func.count(ChannelJoin.id)).where(
        ChannelJoin.channel_id == channel_id
    )

    if active_only:
        stmt = stmt.where(ChannelJoin.is_joined.is_(True))

    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def count_channel_left_users(
    session: AsyncSession,
    channel_id: int,
) -> int:
    result = await session.execute(
        select(func.count(ChannelJoin.id)).where(
            ChannelJoin.channel_id == channel_id,
            ChannelJoin.is_joined.is_(False),
        )
    )
    return int(result.scalar_one() or 0)


async def count_channel_new_joins_since(
    session: AsyncSession,
    channel_id: int,
    days: int,
) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(func.count(ChannelJoin.id)).where(
            ChannelJoin.channel_id == channel_id,
            ChannelJoin.created_at >= threshold,
        )
    )
    return int(result.scalar_one() or 0)


async def count_channel_leaves_since(
    session: AsyncSession,
    channel_id: int,
    days: int,
) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(func.count(ChannelJoin.id)).where(
            ChannelJoin.channel_id == channel_id,
            ChannelJoin.left_at.is_not(None),
            ChannelJoin.left_at >= threshold,
        )
    )
    return int(result.scalar_one() or 0)
