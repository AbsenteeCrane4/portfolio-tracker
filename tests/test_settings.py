"""Settings load from the environment, validate loudly, and never leak secrets."""

from __future__ import annotations

import traceback
from pathlib import Path

import pytest

from portfolio.core.settings import Settings, SettingsError, load_settings

# Marker string that must never surface in any error text or dump.
CANARY = "hunter2-canary"
DB_URL = f"postgresql+asyncpg://app:{CANARY}@db.example.internal:5432/portfolio"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every setting from the process environment so tests are hermetic."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def load(**overrides: object) -> Settings:
    return load_settings(env_file=None, **overrides)


def test_minimal_environment_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = load()

    assert settings.database_url.get_secret_value() == DB_URL
    assert settings.base_currency == "GBP"
    assert (settings.tax_year_start_month, settings.tax_year_start_day) == (4, 6)
    assert settings.log_level == "INFO"
    assert settings.providers == {}


def test_missing_database_url_names_the_key() -> None:
    with pytest.raises(SettingsError) as info:
        load()

    assert "DATABASE_URL" in str(info.value)


def test_malformed_database_url_never_echoes_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"mysql://app:{CANARY}@host/db")

    with pytest.raises(SettingsError) as info:
        load()

    rendered = "".join(traceback.format_exception(info.value))
    assert "DATABASE_URL" in rendered
    assert CANARY not in rendered


def test_all_errors_are_reported_together(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "loud")
    monkeypatch.setenv("TWELVEDATA_DAILY_QUOTA", "0")

    with pytest.raises(SettingsError) as info:
        load()

    message = str(info.value)
    assert "DATABASE_URL" in message
    assert "LOG_LEVEL" in message
    assert "TWELVEDATA_DAILY_QUOTA" in message


def test_log_level_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("LOG_LEVEL", " debug ")

    assert load().log_level == "DEBUG"


@pytest.mark.parametrize("raw", ["usd", " Eur "])
def test_base_currency_is_normalised(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("BASE_CURRENCY", raw)

    assert load().base_currency == raw.strip().upper()


@pytest.mark.parametrize("raw", ["£", "GBPX", "12"])
def test_base_currency_must_be_iso_4217_shaped(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("BASE_CURRENCY", raw)

    with pytest.raises(SettingsError, match="BASE_CURRENCY"):
        load()


def test_tax_year_start_must_be_a_real_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("TAX_YEAR_START_MONTH", "2")
    monkeypatch.setenv("TAX_YEAR_START_DAY", "30")

    with pytest.raises(SettingsError, match="TAX_YEAR_START_MONTH/TAX_YEAR_START_DAY"):
        load()


def test_provider_with_key_is_exposed_with_its_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("TWELVEDATA_API_KEY", CANARY)
    monkeypatch.setenv("FINNHUB_API_KEY", CANARY)
    monkeypatch.setenv("FINNHUB_DAILY_QUOTA", "1234")

    providers = load().providers

    assert set(providers) == {"twelvedata", "finnhub"}
    assert providers["twelvedata"].daily_quota == 800
    assert providers["finnhub"].daily_quota == 1234
    assert providers["finnhub"].api_key.get_secret_value() == CANARY


def test_provider_quota_without_key_does_not_wire_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("TIINGO_DAILY_QUOTA", "10")

    assert "tiingo" not in load().providers


def test_secrets_are_masked_in_repr_and_dumps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("EODHD_API_KEY", CANARY)

    settings = load()

    for rendered in (repr(settings), str(settings), str(settings.model_dump(mode="json"))):
        assert CANARY not in rendered
    assert CANARY not in repr(settings.providers["eodhd"])


def test_settings_are_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    settings = load()

    with pytest.raises(Exception, match="frozen"):
        settings.base_currency = "USD"


def test_dotenv_is_read_beneath_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL={DB_URL}\nBASE_CURRENCY=USD\nNEXT_PUBLIC_UNRELATED=1\n", encoding="utf-8"
    )
    monkeypatch.setenv("BASE_CURRENCY", "EUR")

    settings = load_settings(env_file=env_file)

    assert settings.database_url.get_secret_value() == DB_URL
    assert settings.base_currency == "EUR", "process environment wins over .env"


def test_explicit_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    assert load(log_level="ERROR").log_level == "ERROR"


def test_env_example_lists_every_key_and_no_secrets() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    entries = dict(
        line.split("=", 1)
        for line in example.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )

    assert set(entries) == {name.upper() for name in Settings.model_fields}
    for name, value in entries.items():
        if name.endswith("_API_KEY"):
            assert value == "", f"{name} must be blank in .env.example"
