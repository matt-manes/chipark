from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.tools import config as config_module
from backend.tools.config import Config, ConfigError, EnvValueParser


@dataclass(frozen=True, init=False)
class BooleanConfig(Config):
    enabled: bool


@dataclass(frozen=True, init=False)
class UnsupportedTypeConfig(Config):
    options: list[str]


@pytest.fixture(autouse=True)
def reset_config_singleton(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv_path: Path = tmp_path / ".env"
    dotenv_path.write_text(
        'CHIPARK_DATABASE="postgresql"\n'
        "CHIPARK_CONDITIONS_TTL=900\n"
        'CHIPARK_CORS_ALLOW_LIST="http://localhost:5173"\n'
        'CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL="http://localhost:5173/auth/callback"\n'
        'CHIPARK_PG_URL="postgresql+psycopg2://localhost:5432/chipark"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)
    monkeypatch.setattr(Config, "_instance", None)
    for field_name in (
        "CHIPARK_DATABASE",
        "CHIPARK_CONDITIONS_TTL",
        "CHIPARK_CORS_ALLOW_LIST",
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL",
        "CHIPARK_PG_URL",
        "CHIPARK_ADMIN_EMAIL",
        "CHIPARK_ADMIN_PASSWORD",
        "CHIPARK_WEATHERAPI_KEY",
        "CHIPARK_PG_USER",
        "CHIPARK_PG_PASS",
        "CHIPARK_GOOGLE_CLIENT_ID",
        "CHIPARK_GOOGLE_CLIENT_SECRET",
        "CHIPARK_GOOGLE_REDIRECT_URI",
        "CHIPARK_TEST_PG_URL",
        "CHIPARK_TEST_PG_USER",
        "CHIPARK_TEST_PG_PASSWORD",
        "OTEL_SERVICE_NAME",
        "OTEL_RESOURCE_ATTRIBUTES",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
        "enabled",
        "options",
    ):
        monkeypatch.delenv(field_name, raising=False)


def test_raises_when_required_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv_path: Path = tmp_path / "empty.env"
    dotenv_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)

    with pytest.raises(ConfigError, match="CHIPARK_DATABASE.*missing"):
        Config()


def test_environment_values_are_used_when_dotenv_keys_are_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv_path: Path = tmp_path / "empty.env"
    dotenv_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)
    monkeypatch.setenv("CHIPARK_DATABASE", "sqlite")
    monkeypatch.setenv("CHIPARK_CONDITIONS_TTL", "300")
    monkeypatch.setenv(
        "CHIPARK_CORS_ALLOW_LIST",
        "http://localhost:5173,https://chipark.example.com",
    )
    monkeypatch.setenv(
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL",
        "https://frontend.example.com/auth/callback",
    )
    monkeypatch.setenv("CHIPARK_PG_URL", "postgresql+psycopg2://db.example/chipark")

    config: Config = Config()

    assert config.CHIPARK_DATABASE == "sqlite"
    assert config.CHIPARK_CONDITIONS_TTL == 300
    assert config.cors_allow_origins == (
        "http://localhost:5173",
        "https://chipark.example.com",
    )
    assert (
        config.CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL
        == "https://frontend.example.com/auth/callback"
    )
    assert config.CHIPARK_PG_URL == "postgresql+psycopg2://db.example/chipark"


def test_dotenv_values_override_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv_path: Path = tmp_path / "override.env"
    dotenv_path.write_text(
        'CHIPARK_DATABASE="sqlite"\n'
        "CHIPARK_CONDITIONS_TTL=900\n"
        'CHIPARK_CORS_ALLOW_LIST="http://localhost:5173"\n'
        'CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL="http://localhost:5173/auth/callback"\n'
        'CHIPARK_PG_URL="postgresql+psycopg2://localhost:5432/chipark"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)
    monkeypatch.setenv("CHIPARK_DATABASE", "postgresql")

    config: Config = Config()

    assert config.CHIPARK_DATABASE == "sqlite"


def test_loads_optional_settings_from_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv_path: Path = tmp_path / "credentials.env"
    dotenv_path.write_text(
        'CHIPARK_DATABASE="postgresql"\n'
        "CHIPARK_CONDITIONS_TTL=900\n"
        'CHIPARK_CORS_ALLOW_LIST="http://localhost:5173"\n'
        'CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL="http://localhost:5173/auth/callback"\n'
        'CHIPARK_PG_URL="postgresql+psycopg2://localhost:5432/chipark"\n'
        "CHIPARK_ADMIN_EMAIL=admin@example.com\n"
        "CHIPARK_GOOGLE_CLIENT_ID=google-client\n"
        "CHIPARK_TEST_PG_USER=test-user\n"
        "CHIPARK_TEST_PG_PASSWORD=test-password\n"
        "OTEL_SERVICE_NAME=chipark-test\n"
        "OTEL_RESOURCE_ATTRIBUTES=deployment.environment=test\n"
        "OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.example.com\n"
        "OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer test-token\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)

    config: Config = Config()

    assert config.CHIPARK_ADMIN_EMAIL == "admin@example.com"
    assert config.CHIPARK_GOOGLE_CLIENT_ID == "google-client"
    assert config.CHIPARK_TEST_PG_USER == "test-user"
    assert config.CHIPARK_TEST_PG_PASSWORD == "test-password"
    assert config.CHIPARK_ADMIN_PASSWORD is None
    assert config.OTEL_SERVICE_NAME == "chipark-test"
    assert config.OTEL_RESOURCE_ATTRIBUTES == "deployment.environment=test"
    assert config.OTEL_EXPORTER_OTLP_ENDPOINT == "https://otlp.example.com"
    assert config.OTEL_EXPORTER_OTLP_HEADERS == "Authorization=Bearer test-token"


def test_reuses_singleton_without_reloading(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first_config: Config = Config()
    dotenv_path: Path = tmp_path / "updated.env"
    dotenv_path.write_text(
        'CHIPARK_DATABASE="sqlite"\n'
        "CHIPARK_CONDITIONS_TTL=900\n"
        'CHIPARK_CORS_ALLOW_LIST="http://localhost:5173"\n'
        'CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL="http://localhost:5173/auth/callback"\n'
        'CHIPARK_PG_URL="postgresql+psycopg2://localhost:5432/chipark"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "DOTENV_PATH", dotenv_path)

    second_config: Config = Config()

    assert second_config is first_config
    assert second_config.CHIPARK_DATABASE == "postgresql"


def test_raises_when_subclass_field_has_no_value() -> None:
    with pytest.raises(ConfigError, match="enabled.*missing"):
        BooleanConfig()


def test_config_wraps_invalid_environment_value_with_field_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("enabled", "yes")

    with pytest.raises(ConfigError, match="enabled.*invalid value"):
        BooleanConfig()


def test_config_wraps_unsupported_environment_type_with_field_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("options", "value")

    with pytest.raises(ConfigError, match="options.*unsupported type"):
        UnsupportedTypeConfig()


@pytest.mark.parametrize(
    ("raw_value", "expected_value"),
    [("true", True), ("TRUE", True), ("false", False), ("FALSE", False)],
)
def test_parses_boolean_environment_values(
    raw_value: str, expected_value: bool
) -> None:
    parsed_value: object = EnvValueParser.parse(raw_value, bool)

    assert parsed_value is expected_value


def test_parses_integer_environment_value() -> None:
    parsed_value: object = EnvValueParser.parse("5432", int)

    assert parsed_value == 5432
    assert isinstance(parsed_value, int)


def test_parses_float_environment_value() -> None:
    parsed_value: object = EnvValueParser.parse("2.75", float)

    assert parsed_value == 2.75
    assert isinstance(parsed_value, float)


def test_rejects_unsupported_environment_field_type() -> None:
    with pytest.raises(TypeError, match="Unsupported environment field type"):
        EnvValueParser.parse("value", list)
