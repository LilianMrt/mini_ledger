import os
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

REPO_ROOT = Path(__file__).parent.parent

TEST_DB_USER = "mini_ledger_user"
TEST_DB_PASSWORD = "mini_ledger_password"
TEST_DB_NAME = "mini_ledger_db"


@pytest.fixture(scope="session")
async def postgres_container():
    with PostgresContainer(
        "postgres:15",
        username=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        dbname=TEST_DB_NAME,
        driver=None,
    ) as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))

        os.environ["DB_HOST"] = host
        os.environ["DB_PORT"] = str(port)
        os.environ["DB_NAME"] = TEST_DB_NAME
        os.environ["DB_USER"] = TEST_DB_USER
        os.environ["DB_PASSWORD"] = TEST_DB_PASSWORD

        conn = await asyncpg.connect(
            host=host, port=port, database=TEST_DB_NAME,
            user=TEST_DB_USER, password=TEST_DB_PASSWORD,
        )
        try:
            await conn.execute((REPO_ROOT / "initialization" / "01_schema.sql").read_text())
            await conn.execute((REPO_ROOT / "initialization" / "02_mock_seed.sql").read_text())
        finally:
            await conn.close()

        from app.database import init_db_pool
        await init_db_pool()

        yield container


@pytest.fixture
async def client(postgres_container):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_pool(postgres_container):
    import app.database as database

    return database._pool


@pytest.fixture(autouse=True)
async def clean_tables(db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE entries, transactions, idempotency_keys CASCADE;")
    yield
