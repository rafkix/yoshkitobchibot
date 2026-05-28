from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Channel


async def add_channel(
    session: AsyncSession,
    link_type: str,
    title: str | None = None,
    telegram_chat_id: int | None = None,
    channel_link: str | None = None,
    is_private: bool = False,
    requires_check: bool | None = None,
    previous_subscribers_count: int | None = None,
    current_subscribers_count: int | None = None,
    is_active: bool = True,
) -> Channel | None:
    try:
        if telegram_chat_id is not None:
            existing_by_chat_id = await session.scalar(
                select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
            )
            if existing_by_chat_id:
                return None

        if channel_link is not None:
            existing_by_link = await session.scalar(
                select(Channel).where(Channel.channel_link == channel_link)
            )
            if existing_by_link:
                return None

        if requires_check is None:
            requires_check = link_type != "external_link"

        new_channel = Channel(
            title=title,
            telegram_chat_id=telegram_chat_id,
            channel_link=channel_link,
            link_type=link_type,
            is_private=is_private,
            requires_check=requires_check,
            previous_subscribers_count=previous_subscribers_count,
            current_subscribers_count=current_subscribers_count,
            is_active=is_active,
        )
        session.add(new_channel)
        await session.commit()
        await session.refresh(new_channel)
        return new_channel

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Kanal qo‘shishda xatolik: {e}")
        return None


async def get_channel_by_id(
    session: AsyncSession,
    channel_id: int,
) -> Channel | None:
    result = await session.execute(
        select(Channel).where(Channel.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_chat_id(
    session: AsyncSession,
    telegram_chat_id: int,
) -> Channel | None:
    result = await session.execute(
        select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_link(
    session: AsyncSession,
    channel_link: str,
) -> Channel | None:
    result = await session.execute(
        select(Channel).where(Channel.channel_link == channel_link)
    )
    return result.scalar_one_or_none()


async def get_all_channels(
    session: AsyncSession,
    active_only: bool = False,
) -> list[Channel]:
    stmt = select(Channel).order_by(Channel.created_at.desc())

    if active_only:
        stmt = stmt.where(Channel.is_active.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_channels_by_type(
    session: AsyncSession,
    link_type: str,
    active_only: bool = False,
) -> list[Channel]:
    stmt = (
        select(Channel)
        .where(Channel.link_type == link_type)
        .order_by(Channel.created_at.desc())
    )

    if active_only:
        stmt = stmt.where(Channel.is_active.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_channel(
    session: AsyncSession,
    channel_id: int,
    title: str | None = None,
    telegram_chat_id: int | None = None,
    channel_link: str | None = None,
    link_type: str | None = None,
    is_private: bool | None = None,
    requires_check: bool | None = None,
    previous_subscribers_count: int | None = None,
    current_subscribers_count: int | None = None,
    is_active: bool | None = None,
) -> Channel | None:
    try:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return None

        if (
            telegram_chat_id is not None
            and telegram_chat_id != channel.telegram_chat_id
        ):
            existing_by_chat_id = await session.scalar(
                select(Channel).where(
                    Channel.telegram_chat_id == telegram_chat_id,
                    Channel.channel_id != channel_id,
                )
            )
            if existing_by_chat_id:
                return None
            channel.telegram_chat_id = telegram_chat_id

        if channel_link is not None and channel_link != channel.channel_link:
            existing_by_link = await session.scalar(
                select(Channel).where(
                    Channel.channel_link == channel_link,
                    Channel.channel_id != channel_id,
                )
            )
            if existing_by_link:
                return None
            channel.channel_link = channel_link

        if title is not None:
            channel.title = title

        if link_type is not None:
            channel.link_type = link_type

        if is_private is not None:
            channel.is_private = is_private

        if requires_check is not None:
            channel.requires_check = requires_check

        if previous_subscribers_count is not None:
            channel.previous_subscribers_count = previous_subscribers_count

        if current_subscribers_count is not None:
            channel.current_subscribers_count = current_subscribers_count

        if is_active is not None:
            channel.is_active = is_active

        await session.commit()
        await session.refresh(channel)
        return channel

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Kanalni yangilashda xatolik: {e}")
        return None


async def update_channel_subscribers(
    session: AsyncSession,
    channel_id: int,
    new_count: int,
) -> Channel | None:
    try:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return None

        channel.previous_subscribers_count = channel.current_subscribers_count
        channel.current_subscribers_count = new_count

        await session.commit()
        await session.refresh(channel)
        return channel

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Subscriber count yangilashda xatolik: {e}")
        return None


async def set_channel_active(
    session: AsyncSession,
    channel_id: int,
    is_active: bool,
) -> Channel | None:
    try:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return None

        channel.is_active = is_active
        await session.commit()
        await session.refresh(channel)
        return channel

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Kanal statusini yangilashda xatolik: {e}")
        return None


async def delete_channel(
    session: AsyncSession,
    channel_id: int,
) -> bool:
    try:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            return False

        await session.delete(channel)
        await session.commit()
        return True

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Kanalni o‘chirishda xatolik: {e}")
        return False


async def count_channels(
    session: AsyncSession,
    active_only: bool = False,
) -> int:
    stmt = select(func.count(Channel.channel_id))

    if active_only:
        stmt = stmt.where(Channel.is_active.is_(True))

    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def count_channels_by_type(
    session: AsyncSession,
    link_type: str,
    active_only: bool = False,
) -> int:
    stmt = select(func.count(Channel.channel_id)).where(Channel.link_type == link_type)

    if active_only:
        stmt = stmt.where(Channel.is_active.is_(True))

    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)
