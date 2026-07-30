import os
import asyncpg

_pool = None

async def init_db_pool():
    """Initializes a global connection pool."""
    global _pool
    if not _pool:
        _pool = await asyncpg.create_pool(
            host= os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            min_size=5,
            max_size=20
        )

async def get_db():
    """Yields a database connection from the pool."""
    global _pool
    async with _pool.acquire() as connection:
        yield connection