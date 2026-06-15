"""
Run this once to create all tables in Neon:
    python init_db.py

Safe to re-run — create_all skips existing tables, and the index
statements use IF NOT EXISTS so they apply to an already-created DB.
"""
import asyncio
from sqlalchemy import text
from app.database import engine, Base
import app.models  # noqa — ensures models are registered


# create_all only adds indexes when it creates the table itself, so for an
# existing database these must be applied explicitly.
INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_messages_session_created "
    "ON messages (session_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_tool_calls_message_id "
    "ON tool_calls (message_id)",
    "CREATE INDEX IF NOT EXISTS ix_sessions_user_updated "
    "ON sessions (user_id, updated_at)",
    "CREATE INDEX IF NOT EXISTS ix_sessions_user_id "
    "ON sessions (user_id)",
]

# Light-touch migrations for columns added after the initial schema. Each one
# must be idempotent so re-running init_db.py is always safe.
MIGRATIONS = [
    "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id VARCHAR(100)",
]


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in MIGRATIONS:
            await conn.execute(text(stmt))
        for stmt in INDEXES:
            await conn.execute(text(stmt))
    print("All tables, columns, and indexes created.")
    await engine.dispose()


asyncio.run(main())
