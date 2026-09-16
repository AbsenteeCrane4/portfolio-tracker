"""baseline

Revision ID: 000000000001
Revises:
Create Date: 2026-09-16
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "000000000001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Empty on purpose: this pins the start of the migration chain so every
    # later schema change has a parent. Do not add DDL here.
    pass


def downgrade() -> None:
    pass
