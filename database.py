import os
import asyncpg
from contextlib import asynccontextmanager

# Get DATABASE_URL from environment (Render will provide this)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Timex88@localhost:5432/veritas_db"  # fallback for local dev
)

# Render uses 'postgres://' but asyncpg needs 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Global connection pool
db_pool = None

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        command_timeout=60
    )
    print("✅ Database pool created")

async def close_db():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        print("✅ Database pool closed")

async def get_db():
    """Get database connection from pool"""
    async with db_pool.acquire() as connection:
        yield connection