#!/usr/bin/env python3
"""
Migration: yangi jadvallar va ustunlarni yaratish.
Agar jadvallar allaqachon mavjud bo‘lsa, xato bermaydi.

Ishlatish: python3 migrate.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import engine
from database.models import BotSettings, CustomButton
from sqlalchemy import inspect, text


async def add_column_if_missing(conn, table_name: str, column_name: str, ddl: str):
    def has_column(sync_conn):
        inspector = inspect(sync_conn)
        return any(col["name"] == column_name for col in inspector.get_columns(table_name))

    if await conn.run_sync(has_column):
        print(f"ℹ️  {table_name}.{column_name} allaqachon mavjud")
        return

    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
    print(f"✅ {table_name}.{column_name} ustuni qo‘shildi")


async def rebuild_test_sessions_if_needed(conn):
    def needs_rebuild(sync_conn):
        inspector = inspect(sync_conn)
        unique_constraints = inspector.get_unique_constraints("test_sessions")
        for constraint in unique_constraints:
            if constraint.get("column_names") == ["user_id"]:
                return True
        return False

    if not await conn.run_sync(needs_rebuild):
        print("ℹ️  test_sessions unique cheklovi to‘g‘ri")
        return

    await conn.execute(text("ALTER TABLE test_sessions RENAME TO test_sessions_old"))
    await conn.execute(text("""
        CREATE TABLE test_sessions (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL,
            test_id INTEGER NOT NULL,
            question_ids JSON NOT NULL,
            answers JSON,
            rasch_score FLOAT,
            is_completed BOOLEAN,
            duration_seconds INTEGER,
            started_at DATETIME,
            completed_at DATETIME,
            CONSTRAINT uq_test_session_user_test UNIQUE (user_id, test_id),
            FOREIGN KEY(user_id) REFERENCES users (user_id),
            FOREIGN KEY(test_id) REFERENCES tests (id)
        )
    """))
    await conn.execute(text("""
        INSERT OR IGNORE INTO test_sessions (
            id, user_id, test_id, question_ids, answers, rasch_score,
            is_completed, duration_seconds, started_at, completed_at
        )
        SELECT
            id, user_id, test_id, question_ids, answers, rasch_score,
            is_completed, duration_seconds, started_at, completed_at
        FROM test_sessions_old
    """))
    await conn.execute(text("DROP TABLE test_sessions_old"))
    print("✅ test_sessions unique cheklovi user_id + test_id ko‘rinishiga o‘tkazildi")


async def run_migration():
    async with engine.begin() as conn:
        # Mavjud jadvallarni tekshirish
        def check_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()

        existing = await conn.run_sync(check_tables)
        print(f"Mavjud jadvallar: {existing}")

        # Faqat yangi jadvallarni yaratish
        if "bot_settings" not in existing:
            await conn.run_sync(BotSettings.__table__.create)
            print("✅ bot_settings jadvali yaratildi")
        else:
            print("ℹ️  bot_settings allaqachon mavjud")

        if "custom_buttons" not in existing:
            await conn.run_sync(CustomButton.__table__.create)
            print("✅ custom_buttons jadvali yaratildi")
        else:
            print("ℹ️  custom_buttons allaqachon mavjud")

        if "tests" in existing:
            await add_column_if_missing(conn, "tests", "starts_at", "starts_at DATETIME")
            await add_column_if_missing(conn, "tests", "ends_at", "ends_at DATETIME")

        if "referral_contests" in existing:
            await add_column_if_missing(
                conn,
                "referral_contests",
                "button_text",
                "button_text TEXT",
            )

        if "test_sessions" in existing:
            await rebuild_test_sessions_if_needed(conn)

    print("\n✅ Migration muvaffaqiyatli yakunlandi!")
    print("\nDefaultsozlamalar birinchi ishlatilganda avtomatik yuklanadi.")


if __name__ == "__main__":
    asyncio.run(run_migration())
