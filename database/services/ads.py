from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Ad


async def add_ad(
    session: AsyncSession,
    title: str | None = None,
    description: str | None = None,
    buttons: list | None = None,
) -> Ad | None:
    try:
        new_ad = Ad(
            title=title,
            description=description,
            buttons=buttons or [],
        )
        session.add(new_ad)
        await session.commit()
        await session.refresh(new_ad)
        return new_ad

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Reklama qo‘shishda xatolik: {e}")
        return None


async def get_ad_by_id(session: AsyncSession, ad_id: int) -> Ad | None:
    result = await session.execute(select(Ad).where(Ad.ad_id == ad_id))
    return result.scalar_one_or_none()


async def get_all_ads(session: AsyncSession) -> list[Ad]:
    result = await session.execute(select(Ad).order_by(Ad.created_at.desc()))
    return list(result.scalars().all())


async def get_active_ads(session: AsyncSession) -> list[Ad]:
    result = await session.execute(
        select(Ad).where(Ad.is_active.is_(True)).order_by(Ad.created_at.desc())
    )
    return list(result.scalars().all())


async def update_ad(
    session: AsyncSession,
    ad_id: int,
    title: str | None = None,
    description: str | None = None,
    buttons: list | None = None,
    is_active: bool | None = None,
) -> Ad | None:
    try:
        ad = await get_ad_by_id(session, ad_id)
        if not ad:
            return None

        if title is not None:
            ad.title = title

        if description is not None:
            ad.description = description

        if buttons is not None:
            ad.buttons = buttons

        if is_active is not None:
            ad.is_active = is_active

        await session.commit()
        await session.refresh(ad)
        return ad

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Reklamani yangilashda xatolik: {e}")
        return None


async def set_ad_active(
    session: AsyncSession,
    ad_id: int,
    is_active: bool,
) -> Ad | None:
    try:
        ad = await get_ad_by_id(session, ad_id)
        if not ad:
            return None

        ad.is_active = is_active
        await session.commit()
        await session.refresh(ad)
        return ad

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Reklama statusini yangilashda xatolik: {e}")
        return None


async def delete_ad(session: AsyncSession, ad_id: int) -> bool:
    try:
        ad = await get_ad_by_id(session, ad_id)
        if not ad:
            return False

        await session.delete(ad)
        await session.commit()
        return True

    except SQLAlchemyError as e:
        await session.rollback()
        print(f"❌ Reklamani o‘chirishda xatolik: {e}")
        return False


async def count_ads(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Ad.ad_id)))
    return int(result.scalar_one() or 0)


async def count_active_ads(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(Ad.ad_id)).where(Ad.is_active.is_(True))
    )
    return int(result.scalar_one() or 0)
