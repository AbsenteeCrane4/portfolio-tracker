"""Typed application settings.

Configuration comes from environment variables (plus a ``.env`` file in
development), is validated once at startup by :func:`load_settings`, and travels
through ``AppContext``. Nothing else in the codebase reads ``os.environ`` —
``tests/test_layout.py`` enforces that.

Secrets are ``SecretStr`` so they are masked in ``repr``, ``str``, and
``model_dump(mode="json")``. Validation failures are re-raised as
:class:`SettingsError`, which names the offending key but never echoes its value.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["LogLevel", "ProviderSettings", "Settings", "SettingsError", "load_settings"]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_CURRENCY_CODE = re.compile(r"[A-Z]{3}")


class SettingsError(RuntimeError):
    """Configuration is missing or malformed.

    The message lists the offending environment variable names and what is wrong
    with them. It deliberately contains no input values, because those may be
    secrets.
    """


class ProviderSettings(BaseModel, frozen=True):
    """Resolved configuration for one external data provider that has an API key."""

    name: str
    api_key: SecretStr
    daily_quota: int = Field(gt=0)


class Settings(BaseSettings):
    """All application configuration, loaded from the environment.

    Construct via :func:`load_settings`, not directly, so that validation errors
    surface as :class:`SettingsError`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        # The repo root `.env` is shared with the Next.js frontend, so unknown keys
        # are expected. Environment variables are matched by field name regardless.
        extra="ignore",
    )

    # --- required ---------------------------------------------------------------
    database_url: SecretStr

    # --- portfolio ----------------------------------------------------------------
    base_currency: str = "GBP"
    tax_year_start_month: int = Field(default=4, ge=1, le=12)
    tax_year_start_day: int = Field(default=6, ge=1, le=31)

    # --- observability ------------------------------------------------------------
    log_level: LogLevel = "INFO"

    # --- providers ----------------------------------------------------------------
    # A provider with no API key is simply not wired. Daily quota defaults follow
    # the free-tier table in CLAUDE.md; verify against the provider before relying
    # on them.
    twelvedata_api_key: SecretStr | None = None
    twelvedata_daily_quota: int = Field(default=800, gt=0)

    finnhub_api_key: SecretStr | None = None
    finnhub_daily_quota: int = Field(default=5000, gt=0)

    alphavantage_api_key: SecretStr | None = None
    alphavantage_daily_quota: int = Field(default=25, gt=0)

    tiingo_api_key: SecretStr | None = None
    tiingo_daily_quota: int = Field(default=50, gt=0)

    fmp_api_key: SecretStr | None = None
    fmp_daily_quota: int = Field(default=250, gt=0)

    eodhd_api_key: SecretStr | None = None
    eodhd_daily_quota: int = Field(default=20, gt=0)

    @field_validator("database_url")
    @classmethod
    def _postgres_scheme(cls, value: SecretStr) -> SecretStr:
        scheme = urlsplit(value.get_secret_value()).scheme
        if scheme != "postgresql" and not scheme.startswith("postgresql+"):
            raise ValueError("must be a postgresql:// or postgresql+<driver>:// URL")
        return value

    @field_validator("base_currency", mode="before")
    @classmethod
    def _normalise_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("base_currency")
    @classmethod
    def _iso_currency(cls, value: str) -> str:
        if not _CURRENCY_CODE.fullmatch(value):
            raise ValueError("must be a three-letter ISO 4217 code such as GBP")
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _tax_year_start_is_a_date(self) -> Settings:
        try:
            # Non-leap year: 29 February is never a valid tax year start.
            date(2001, self.tax_year_start_month, self.tax_year_start_day)
        except ValueError:
            raise ValueError(
                "TAX_YEAR_START_MONTH/TAX_YEAR_START_DAY do not form a valid calendar date"
            ) from None
        return self

    @property
    def providers(self) -> dict[str, ProviderSettings]:
        """Providers that have an API key configured, keyed by name."""
        candidates = {
            "twelvedata": (self.twelvedata_api_key, self.twelvedata_daily_quota),
            "finnhub": (self.finnhub_api_key, self.finnhub_daily_quota),
            "alphavantage": (self.alphavantage_api_key, self.alphavantage_daily_quota),
            "tiingo": (self.tiingo_api_key, self.tiingo_daily_quota),
            "fmp": (self.fmp_api_key, self.fmp_daily_quota),
            "eodhd": (self.eodhd_api_key, self.eodhd_daily_quota),
        }
        return {
            name: ProviderSettings(name=name, api_key=key, daily_quota=quota)
            for name, (key, quota) in candidates.items()
            if key is not None
        }


def load_settings(env_file: str | Path | None = ".env", **overrides: Any) -> Settings:
    """Build :class:`Settings` from the environment, failing loudly on bad config.

    Args:
        env_file: Dotenv file to read beneath the process environment. Pass
            ``None`` to read the environment only (tests do this).
        **overrides: Explicit field values, which take precedence over both.

    Raises:
        SettingsError: naming every missing or malformed key, with no values.
    """
    # `_env_file` is a real BaseSettings kwarg, but the dataclass_transform-generated
    # signature mypy sees only lists model fields, so it goes in via the dict.
    kwargs: dict[str, Any] = {"_env_file": env_file, **overrides}
    try:
        return Settings(**kwargs)
    except ValidationError as exc:
        # `from None` matters: the ValidationError's own repr includes input values.
        raise SettingsError(_describe(exc)) from None


def _describe(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        key = "/".join(str(part).upper() for part in error["loc"]) or "SETTINGS"
        lines.append(f"  {key}: {error['msg']}")
    return "invalid configuration:\n" + "\n".join(lines)
