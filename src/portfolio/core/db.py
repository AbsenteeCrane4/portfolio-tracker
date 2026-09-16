"""Async database layer: declarative base, column type helpers, engine and sessions.

Everything that touches Postgres goes through here. Models inherit from
:class:`Base`, which fixes two things globally:

* a naming convention, so every constraint and index has a deterministic name
  that Alembic can reference in ``downgrade``;
* a type map that turns ``Mapped[Decimal]`` into ``NUMERIC`` and
  ``Mapped[datetime]`` into ``TIMESTAMPTZ``, so the money-is-Decimal and
  datetimes-are-UTC rules in CLAUDE.md hold without every model restating them.

Money and quantity columns should use the :data:`Money` and :data:`Quantity`
annotations rather than a bare ``Decimal`` so their precision is consistent
across migrations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar

from sqlalchemy import DateTime, MetaData, Numeric
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.types import TypeEngine

from portfolio.core.settings import Settings

__all__ = [
    "MONEY",
    "QUANTITY",
    "Base",
    "Money",
    "Quantity",
    "make_engine",
    "make_session_factory",
]

# Alembic needs stable names to drop constraints in downgrades; Postgres's
# auto-generated ones are not stable across engines or reflection.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Precision is generous on purpose: fractional shares and sub-penny FX-adjusted
# prices are real, and NUMERIC costs nothing extra for unused digits.
MONEY = Numeric(precision=20, scale=8, asdecimal=True)
QUANTITY = Numeric(precision=24, scale=10, asdecimal=True)

Money = Annotated[Decimal, mapped_column(MONEY)]
"""A monetary amount or price. Maps to ``NUMERIC(20, 8)``."""

Quantity = Annotated[Decimal, mapped_column(QUANTITY)]
"""A unit count such as shares held. Maps to ``NUMERIC(24, 10)``."""


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # A bare `Mapped[Decimal]` still lands on NUMERIC rather than FLOAT, and a bare
    # `Mapped[datetime]` is always TIMESTAMPTZ. `float` is deliberately absent:
    # a `Mapped[float]` column is a bug and SQLAlchemy would otherwise map it to
    # FLOAT silently.
    type_annotation_map: ClassVar[dict[type, TypeEngine[Any]]] = {
        Decimal: MONEY,
        datetime: DateTime(timezone=True),
    }


def make_engine(settings: Settings, **kwargs: object) -> AsyncEngine:
    """Create the application's async engine from validated settings.

    Args:
        settings: Loaded application settings; only ``database_url`` is read.
        **kwargs: Passed to :func:`sqlalchemy.ext.asyncio.create_async_engine`,
            e.g. ``poolclass`` for tests.
    """
    return create_async_engine(
        settings.database_url.get_secret_value(),
        echo=settings.log_level == "DEBUG",
        pool_pre_ping=True,
        **kwargs,
    )


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the session factory handed to features through ``AppContext``.

    ``expire_on_commit`` is off because attributes are routinely read after a
    commit in async code, and a lazy refresh there would need an awaited I/O.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
