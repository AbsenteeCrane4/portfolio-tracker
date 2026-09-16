"""Declarative base conventions, engine construction, and the test session fixture.

Tests that take ``db_session`` or ``alembic_config`` need ``TEST_DATABASE_URL``
and skip without it; the rest are pure Python.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, Numeric, Table, UniqueConstraint, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.pool import NullPool

from portfolio.core.db import Base, Money, Quantity, make_engine, make_session_factory
from portfolio.core.settings import load_settings


class Probe(Base):
    """Throwaway model exercising every convention the base is meant to enforce."""

    __tablename__ = "_db_probe"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[Money]
    units: Mapped[Quantity]
    bare_decimal: Mapped[Decimal]
    recorded_at: Mapped[datetime]


PROBE_TABLE: Table = Base.metadata.tables["_db_probe"]


def _numeric(name: str) -> Numeric[Decimal]:
    column_type = PROBE_TABLE.c[name].type
    assert isinstance(column_type, Numeric), name
    return column_type


# --- conventions, no database -----------------------------------------------------


def test_constraints_get_deterministic_names() -> None:
    assert PROBE_TABLE.primary_key.name == "pk__db_probe"
    unique = next(c for c in PROBE_TABLE.constraints if isinstance(c, UniqueConstraint))
    assert unique.name == "uq__db_probe_label"


def test_decimal_annotations_map_to_numeric() -> None:
    for name in ("amount", "units", "bare_decimal"):
        assert _numeric(name).asdecimal, name
    assert (_numeric("amount").precision, _numeric("amount").scale) == (20, 8)
    assert (_numeric("units").precision, _numeric("units").scale) == (24, 10)


def test_datetime_annotation_is_timezone_aware() -> None:
    column_type = PROBE_TABLE.c.recorded_at.type

    assert isinstance(column_type, DateTime)
    assert column_type.timezone


def test_float_is_not_in_the_type_map() -> None:
    assert float not in Base.type_annotation_map


def test_engine_is_built_from_settings() -> None:
    url = "postgresql+asyncpg://app:secret@db.example.internal:5432/portfolio"
    settings = load_settings(env_file=None, database_url=url, log_level="WARNING")

    engine = make_engine(settings, poolclass=NullPool)

    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == "portfolio"
    assert engine.echo is False
    factory = make_session_factory(engine)
    assert factory.kw["expire_on_commit"] is False


# --- against Postgres ---------------------------------------------------------------


async def test_numeric_round_trips_decimals_exactly(db_session: AsyncSession) -> None:
    connection = await db_session.connection()
    await connection.run_sync(PROBE_TABLE.create)

    when = datetime(2026, 4, 6, 9, 30, tzinfo=UTC)
    db_session.add(
        Probe(
            label="probe",
            amount=Decimal("0.1"),
            units=Decimal("1.0000000001"),
            bare_decimal=Decimal("123456789012.12345678"),
            recorded_at=when,
        )
    )
    await db_session.commit()
    db_session.expunge_all()

    row = (await db_session.execute(select(Probe))).scalar_one()
    assert row.amount == Decimal("0.1")
    assert isinstance(row.amount, Decimal)
    assert row.units == Decimal("1.0000000001")
    assert row.bare_decimal == Decimal("123456789012.12345678")
    assert row.recorded_at == when
    assert row.recorded_at.tzinfo is not None


async def test_session_fixture_rolls_back_even_after_commit(
    db_session: AsyncSession, db_engine: AsyncEngine
) -> None:
    await db_session.execute(text("CREATE TABLE _rollback_probe (id integer PRIMARY KEY)"))
    await db_session.execute(text("INSERT INTO _rollback_probe VALUES (1)"))
    await db_session.commit()

    # Visible inside the test's transaction...
    count = await db_session.scalar(text("SELECT count(*) FROM _rollback_probe"))
    assert count == 1

    # ...and invisible to everyone else, so nothing can leak between tests.
    async with db_engine.connect() as other:
        exists = await other.scalar(text("SELECT to_regclass('_rollback_probe') IS NOT NULL"))
    assert exists is False


async def _table_names(url: str) -> list[str]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(lambda c: inspect(c).get_table_names())
    finally:
        await engine.dispose()


def test_migrations_upgrade_and_downgrade_cleanly(
    alembic_config: Config, test_database_url: str
) -> None:
    # Synchronous on purpose: env.py drives its own event loop via asyncio.run,
    # which cannot be nested inside pytest-asyncio's loop.
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    tables = asyncio.run(_table_names(test_database_url))
    assert "alembic_version" in tables
    assert not [t for t in tables if t.startswith("_")], "probe tables leaked from other tests"

    command.downgrade(alembic_config, "base")
    assert asyncio.run(_table_names(test_database_url)) == ["alembic_version"]
