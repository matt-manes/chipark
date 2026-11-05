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
def reset_config_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "_instance", None)
    monkeypatch.delenv("CHIPARK_DATABASE", raising=False)
    monkeypatch.delenv("CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL", raising=False)


def test_loads_database_from_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text(
        'CHIPARK_DATABASE = "sqlite"\n'
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL = "
        '"http://localhost:3000/auth/callback"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    config: Config = Config()

    assert config.CHIPARK_DATABASE == "sqlite"
    assert (
        config.CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL
        == "http://localhost:3000/auth/callback"
    )


def test_environment_value_overrides_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text(
        'CHIPARK_DATABASE = "sqlite"\n'
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL = "
        '"http://localhost:3000/auth/callback"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setenv("CHIPARK_DATABASE", "postgresql")
    monkeypatch.setenv(
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL",
        "https://frontend.example.com/auth/callback",
    )

    config: Config = Config()

    assert config.CHIPARK_DATABASE == "postgresql"
    assert (
        config.CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL
        == "https://frontend.example.com/auth/callback"
    )


def test_reuses_singleton_without_reloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text(
        'CHIPARK_DATABASE = "sqlite"\n'
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL = "
        '"http://localhost:3000/auth/callback"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    first_config: Config = Config()
    config_path.write_text('CHIPARK_DATABASE = "postgresql"\n', encoding="utf-8")
    second_config: Config = Config()

    assert second_config is first_config
    assert second_config.CHIPARK_DATABASE == "sqlite"


def test_raises_when_field_is_missing_from_toml_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    with pytest.raises(ConfigError, match="CHIPARK_DATABASE.*missing"):
        Config()


def test_rejects_invalid_environment_value_for_boolean_field() -> None:
    with pytest.raises(ValueError, match="true.*false"):
        EnvValueParser.parse("yes", bool)


def test_config_wraps_invalid_environment_value_with_field_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text(
        'CHIPARK_DATABASE = "sqlite"\n'
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL = "
        '"http://localhost:3000/auth/callback"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setenv("enabled", "yes")

    with pytest.raises(ConfigError, match="enabled.*invalid value"):
        BooleanConfig()


def test_config_wraps_unsupported_environment_type_with_field_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text(
        'CHIPARK_DATABASE = "sqlite"\n'
        "CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL = "
        '"http://localhost:3000/auth/callback"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
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
