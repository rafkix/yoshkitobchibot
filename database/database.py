from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from database.models import Base

DATABASE_URL = "sqlite+aiosqlite:///database.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
