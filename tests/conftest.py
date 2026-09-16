"""Shared fixtures.

Database-backed tests need ``TEST_DATABASE_URL`` pointing at a Postgres database
they may freely mutate (``docker compose up -d`` provides one, see
``docker-compose.yml``). When it is unset those tests skip rather than fail, so
the pure-Python suite still runs on a machine without Postgres. CI always sets it.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from portfolio.core.settings import Settings, load_settings

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping database-backed tests")
    return url


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    """Settings pointed at the test database, ignoring any local ``.env``."""
    return load_settings(env_file=None, database_url=test_database_url)


@pytest.fixture
def alembic_config(test_database_url: str) -> Config:
    """Alembic config aimed at the test database, bypassing ``DATABASE_URL``."""
    config = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    config.set_main_option("sqlalchemy.url", test_database_url)
    return config


@pytest.fixture
async def db_engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    # One engine per test, with no pool: pytest-asyncio gives each test its own
    # event loop and asyncpg connections cannot be shared across loops.
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session inside an outer transaction that is rolled back after the test.

    Code under test may ``commit()`` freely; that only releases a savepoint. Nothing
    reaches the database permanently, so tests need no cleanup and can run in any
    order.
    """
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
