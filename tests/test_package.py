"""Smoke test: the package imports and reports a version."""

from __future__ import annotations

import portfolio


def test_version_is_exposed() -> None:
    assert portfolio.__version__


async def test_asyncio_auto_mode_is_active() -> None:
    """No `@pytest.mark.asyncio` decorator: proves `asyncio_mode = "auto"` is wired."""
    assert portfolio.__version__
